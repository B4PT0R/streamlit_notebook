import base64
import io
import time
from typing import Optional
import streamlit as st
from pydub import AudioSegment
import filetype
from ..utils import short_id, state_key

# Mapping audio format → MIME type for browser compatibility
AUDIO_FORMAT_TO_MIME = {
    'mp3': 'audio/mpeg',
    'wav': 'audio/wav',
    'ogg': 'audio/ogg',
    'opus': 'audio/opus',
    'webm': 'audio/webm',
    'flac': 'audio/flac',
    'm4a': 'audio/mp4',
    'aac': 'audio/aac',
    'wma': 'audio/x-ms-wma',
}

# --- JavaScript du composant v2 ---
JS = """
export default function(component) {
    const { data, parentElement } = component;
    if (!data || !parentElement) return;

    const { src, volume } = data;
    if (!src) return;

    // Récupère le vrai root (HTMLElement) même si on est dans un Shadow DOM
    const root =
        parentElement instanceof ShadowRoot
            ? parentElement.host
            : parentElement;

    if (!root || !root.style) return;

    // --- Cacher le composant lui-même (performance optimized) ---
    Object.assign(root.style, {
        display: 'none',
        margin: '0',
        padding: '0',
        height: '0',
        width: '0',
        overflow: 'hidden',
        position: 'absolute',
        visibility: 'hidden'
    });

    // --- Cacher le conteneur Streamlit autour ---
    const container =
        root.closest('[data-testid="stElementContainer"]') ||
        root.closest('[data-testid="stVerticalBlock"]') ||
        root.parentElement;

    if (container && container.style) {
        Object.assign(container.style, {
            display: 'none',
            margin: '0',
            padding: '0',
            height: '0',
            width: '0',
            overflow: 'hidden'
        });
    }

    // --- Gestion de l'audio caché avec optimisations ---
    let audio = root.querySelector('audio[data-tts-autoplay]');
    if (!audio) {
        audio = document.createElement('audio');
        audio.setAttribute('data-tts-autoplay', '1');

        // Attributs pour meilleur support cross-browser
        audio.setAttribute('preload', 'auto');
        audio.setAttribute('playsinline', ''); // iOS support

        // Cache complètement l'élément
        Object.assign(audio.style, {
            display: 'none',
            position: 'absolute',
            width: '0',
            height: '0',
            opacity: '0',
            pointerEvents: 'none'
        });

        root.appendChild(audio);
    }

    // Update src seulement si changé (perf)
    if (audio.src !== src) {
        audio.src = src;

        // Force le chargement pour meilleure compatibilité
        audio.load();
    }

    // Set volume (clamp entre 0 et 1 pour sécurité)
    audio.volume = Math.max(0, Math.min(1, volume ?? 1.0));

    // Stratégie de playback robuste multi-browser
    const attemptPlay = async () => {
        try {
            // Modern browsers: Promise-based play
            await audio.play();
        } catch (err) {
            // Fallback pour autoplay bloqué
            console.warn('[AutoPlay] Autoplay blocked, attempting workaround:', err);

            // Strategy 1: User interaction unlocking (pour Safari/iOS)
            const unlockAudio = () => {
                audio.play()
                    .then(() => {
                        console.log('[AutoPlay] Unlocked via user interaction');
                        document.removeEventListener('click', unlockAudio);
                        document.removeEventListener('touchstart', unlockAudio);
                    })
                    .catch(e => console.warn('[AutoPlay] Still blocked:', e));
            };

            // Écoute la prochaine interaction utilisateur
            document.addEventListener('click', unlockAudio, { once: true });
            document.addEventListener('touchstart', unlockAudio, { once: true });

            // Strategy 2: Retry avec mute puis unmute (Chrome workaround)
            if (audio.muted === false) {
                audio.muted = true;
                try {
                    await audio.play();
                    // Unmute progressivement pour éviter le "click"
                    setTimeout(() => { audio.muted = false; }, 100);
                } catch (retryErr) {
                    console.warn('[AutoPlay] Muted retry failed:', retryErr);
                }
            }
        }
    };

    // Vérifier si l'audio est déjà prêt ou attendre
    if (audio.readyState >= 3) { // HAVE_FUTURE_DATA
        attemptPlay();
    } else {
        // Attendre que l'audio soit chargé
        const playWhenReady = () => {
            attemptPlay();
            audio.removeEventListener('canplay', playWhenReady);
        };
        audio.addEventListener('canplay', playWhenReady, { once: true });
    }
}
"""

# On enregistre le composant v2 une seule fois
def _component(*args,**kwargs):
    component_key = state_key("auto_play_component")
    if component_key not in st.session_state:
        st.session_state[component_key] = st.components.v2.component(
            "auto_play_tts",
            js=JS,
        )
    return st.session_state[component_key](*args,**kwargs)

def auto_play_bytes(
    audio_bytes: bytes,
    mime_type: str = "audio/wav",
    *,
    key: Optional[str] = None,
    volume: float = 1.0,
) -> None:
    """Lit un audio (bytes) en autoplay, sans rien afficher dans l'UI."""
    b64 = base64.b64encode(audio_bytes).decode("ascii")
    src = f"data:{mime_type};base64,{b64}"
    _component(
        data={"src": src, "volume": float(volume)},
        key=key or short_id(),
        isolate_styles=False
    )

def auto_play(
    audio: Optional[any],
    format: Optional[str] = None,
    wait: bool = True,
    lag: float = 0.25,
    key: Optional[str] = None
) -> None:
    """Autoplay audio in the Streamlit app without UI.

    Args:
        audio: Audio input - can be:
               - bytes
               - BytesIO
               - AudioSegment
               - None: No audio to play
        format: Audio format ('mp3', 'wav', 'ogg', etc.) - determines MIME type for browser.
                If None (default), format is auto-detected from audio content using magic bytes.
                Explicit format is only needed when auto-detection fails.
        wait: If True, blocks execution until audio finishes playing
        lag: Additional time (seconds) to add after audio duration when waiting
        key: Optional unique key for the component

    Note:
        Audio is sent in the specified/detected format (no conversion to WAV).
        This preserves quality and reduces data transfer significantly.
        MP3 is ~10x smaller than WAV for equivalent duration.
    """
    if audio is None:
        return

    try:
        # Convert to AudioSegment if needed
        if isinstance(audio,bytes):
            audio=io.BytesIO(audio)
        if isinstance(audio, io.BytesIO):
            audio.seek(0)

            # Auto-detect format from magic bytes if not specified
            if format is None:
                audio_bytes_peek = audio.read(261)  # Read enough for magic bytes
                audio.seek(0)  # Reset position

                kind = filetype.guess(audio_bytes_peek)
                if kind is not None and kind.mime.startswith('audio/'):
                    format = kind.extension
                else:
                    # Fallback to mp3 if detection fails
                    format = 'mp3'

            audio=AudioSegment.from_file(audio, format=format)

        if not isinstance(audio,AudioSegment):
            raise TypeError("audio must be bytes, BytesIO, or AudioSegment")

        # If format still None (AudioSegment passed directly), use default
        if format is None:
            format = 'mp3'  # Safe default for export

        # Get duration BEFORE export
        duration = audio.duration_seconds

        # Export in detected/specified format
        buffer = io.BytesIO()
        audio.export(buffer, format=format)
        buffer.seek(0)
        audio_bytes = buffer.getvalue()

        # Double-check format from exported bytes (in case export changed it)
        # This handles edge cases where export might fall back to a different format
        buffer.seek(0)
        detected = filetype.guess(buffer.read(261))
        if detected is not None and detected.mime.startswith('audio/'):
            actual_format = detected.extension
            mime_type = detected.mime
        else:
            # Use specified format
            actual_format = format
            mime_type = AUDIO_FORMAT_TO_MIME.get(format.lower(), f'audio/{format}')

        auto_play_bytes(audio_bytes, mime_type=mime_type, key=key)

        if wait:
            time.sleep(duration + lag)

    except (KeyError, TypeError, ZeroDivisionError) as e:
        st.error(f"Error playing audio: {e}")
    except Exception as e:
        st.error(f"Error processing audio: {e}")
