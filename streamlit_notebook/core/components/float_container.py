"""Float a Streamlit container relative to its parent.

This module provides a tiny v2 component that:
1) Marks the target container in the DOM.
2) Measures its closest parent container.
3) Exposes reference geometry as CSS variables.
4) Applies custom CSS to position the floated container.

Usage:
    from streamlit_notebook.core.components import float_container

    # Inside the container you want to float:
    with st.container():
        float_container(
            ref="my-float",
            container_css=\"\"\"
                position: fixed;
                left: calc(__parent__.geometry.left + 16px);
                top: calc(__parent__.geometry.bottom - 48px);
            \"\"\",
            document_css=\"\"\"
                @media (max-width: 640px) {
                    __child__ { width: 90vw; }
                }
            \"\"\",
        )
        st.button(\"Action\")

    # Align right edge to parent's right padding (dot notation)
    with st.container():
        float_container(
            ref="right-align",
            container_css=\"\"\"
                position: fixed;
                right: calc(__parent__.geometry.right - __parent__.style.padding-right);
                top: calc(__parent__.geometry.top + 8px);
            \"\"\",
        )
        st.button(\"Pinned\")

    # Offset from parent's left padding using computed styles (dot notation)
    with st.container():
        float_container(
            ref="pad-offset",
            container_css=\"\"\"
                position: fixed;
                left: calc(__parent__.geometry.left + __parent__.style.padding-left);
                top: calc(__parent__.geometry.top + 12px);
            \"\"\",
        )
        st.button(\"Pad Offset\")

    # Combine CSS vars and a parent style for bottom placement (dot notation)
    with st.container():
        float_container(
            ref="bottom-stick",
            container_css=\"\"\"
                position: fixed;
                left: __parent__.geometry.center;
                transform: translateX(-50%);
                bottom: calc(16px + __parent__.style.padding-bottom);
            \"\"\",
        )
        st.button(\"Bottom Stick\")

Supported geometry attributes:
    left, right, top, bottom, width, height, center

Supported theme variables (auto-detected from Streamlit's current theme):
    - __theme__.background-color - Main app background color (opaque)
    - __theme__.background-color-alpha - Main app background with transparency (controlled by alpha parameter)
    - __theme__.secondary-background-color - Sidebar/secondary background color (opaque)
    - __theme__.secondary-background-color-alpha - Sidebar background with transparency (controlled by alpha parameter)
    - __theme__.text-color - Primary text color
    - __theme__.border-color - Border color (adapts to light/dark theme)
    - __theme__.primary-color - Streamlit primary/accent color

Parameters:
    ref: Unique identifier for this float container
    container_css: CSS to apply to the floated container
    document_css: Additional CSS to inject into the document
    padding_bottom: Bottom padding for the main content area (default: "7.5rem")
    alpha: Transparency level for -alpha color variants (0.0 = fully transparent, 1.0 = opaque, default: 0.95)

Notes:
    - The float marker is injected inside the container you want to float.
      Its closest Streamlit parent is used as the reference container.
    - The component auto-injects CSS once per group.
    - Use __parent__.geometry.<attr> for parent geometry (left, right, top, bottom,
      width, height, center).
    - Use __parent__.style.<attr> for computed CSS properties from the parent
      container (kebab-case names like ``padding-left``, ``margin-top``).
    - Use __theme__.<variable-name> for theme-aware colors that automatically adapt
      to Streamlit's current theme (light or dark).
    - Use __child__ in document_css to target the floated container selector.
"""

import streamlit as st
import streamlit.components.v2 as v2_components
import textwrap
from ..utils import state_key, short_id

MARKER_JS = """
export default function(component) {
    const { parentElement, data } = component || {};
    if (!data || !parentElement) return;

    const ref = data.ref || "st-notebook-main";

    // Get the root element (handle Shadow DOM)
    const root = parentElement instanceof ShadowRoot ? parentElement.host : parentElement;
    if (!root || !root.style) return;

    // Create the marker element
    const marker = document.createElement('div');
    marker.setAttribute('data-st-float-ref', ref);
    marker.setAttribute('data-st-float-role', 'float');

    // Hide the marker completely
    Object.assign(marker.style, {
        display: 'none',
        margin: '0',
        padding: '0',
        height: '0',
        width: '0',
        overflow: 'hidden',
        position: 'absolute',
        visibility: 'hidden'
    });

    root.appendChild(marker);

    // Hide the component's parentElement
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

    // Hide the Streamlit container around it
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
}
"""

JS = """
export default function(component) {
    const { parentElement, data } = component || {};
    const ref = (data && data.ref) ? data.ref : "st-notebook-main";
    const containerCss = (data && data.containerCss) ? data.containerCss : "";
    const documentCss = (data && data.documentCss) ? data.documentCss : "";
    const paddingBottom = (data && data.paddingBottom) ? data.paddingBottom : "";
    const alpha = (data && data.alpha !== undefined) ? data.alpha : 0.95;
    const styleId = `st-notebook-float-style-${ref}`;
    const root = document.documentElement;
    const floatSelector = `[data-st-float-ref="${ref}"][data-st-float-role="float"]`;
    const containerSelector = `div[data-testid="stVerticalBlock"]:has(${floatSelector}):not(:has(div[data-testid="stVerticalBlock"] ${floatSelector}))`;

    const getFloatContainer = () => {
        const marker = document.querySelector(floatSelector);
        if (!marker) return null;
        return (
            marker.closest('div[data-testid="stVerticalBlock"]') ||
            marker.closest('div.element-container') ||
            marker.parentElement
        );
    };

    const getMain = () => {
        const floatContainer = getFloatContainer();
        if (!floatContainer) return null;
        return floatContainer.parentElement || floatContainer;
    };

    let rafId = null;
    const update = () => {
        if (rafId) return;
        rafId = requestAnimationFrame(() => {
            rafId = null;
            const main = getMain();
            if (!main) return;
            const rect = main.getBoundingClientRect();
            const center = rect.left + rect.width / 2;
            root.style.setProperty(`--st-float-${ref}-left`, rect.left + "px");
            root.style.setProperty(`--st-float-${ref}-right`, rect.right + "px");
            root.style.setProperty(`--st-float-${ref}-top`, rect.top + "px");
            root.style.setProperty(`--st-float-${ref}-bottom`, rect.bottom + "px");
            root.style.setProperty(`--st-float-${ref}-width`, rect.width + "px");
            root.style.setProperty(`--st-float-${ref}-height`, rect.height + "px");
            root.style.setProperty(`--st-float-${ref}-center`, center + "px");

            // Detect and set theme colors
            const appContainer = document.querySelector('[data-testid="stApp"]');
            const sidebar = document.querySelector('[data-testid="stSidebar"]');

            if (appContainer) {
                const bgColor = getComputedStyle(appContainer).backgroundColor;
                const textColor = getComputedStyle(appContainer).color;

                // Determine if theme is dark or light by analyzing background luminance
                const rgb = bgColor.match(/\\d+/g);
                let isDark = true; // default to dark
                if (rgb && rgb.length >= 3) {
                    const r = parseInt(rgb[0]);
                    const g = parseInt(rgb[1]);
                    const b = parseInt(rgb[2]);
                    const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
                    isDark = luminance < 0.5;
                }

                const secondaryBgColor = sidebar ? getComputedStyle(sidebar).backgroundColor :
                                        (isDark ? 'rgb(38, 39, 48)' : 'rgb(240, 242, 246)');
                const borderColor = isDark ? 'rgba(250, 250, 250, 0.2)' : 'rgba(49, 51, 63, 0.2)';

                // Convert background color to rgba with alpha transparency
                const bgColorWithAlpha = bgColor.replace('rgb(', 'rgba(').replace(')', `, ${alpha})`);
                const secondaryBgColorWithAlpha = secondaryBgColor.replace('rgb(', 'rgba(').replace(')', `, ${alpha})`);

                // Set theme color CSS variables
                root.style.setProperty(`--st-float-${ref}-theme-primary-color`, '#ff4b4b');
                root.style.setProperty(`--st-float-${ref}-theme-background-color`, bgColor);
                root.style.setProperty(`--st-float-${ref}-theme-background-color-alpha`, bgColorWithAlpha);
                root.style.setProperty(`--st-float-${ref}-theme-secondary-background-color`, secondaryBgColor);
                root.style.setProperty(`--st-float-${ref}-theme-secondary-background-color-alpha`, secondaryBgColorWithAlpha);
                root.style.setProperty(`--st-float-${ref}-theme-text-color`, textColor);
                root.style.setProperty(`--st-float-${ref}-theme-border-color`, borderColor);
            }
        });
    };

    const ro = new ResizeObserver(update);
    const mo = new MutationObserver(update);
    const main = getMain();
    if (main) {
        ro.observe(main);
    }
    mo.observe(document.body, { attributes: true, childList: true, subtree: true });
    window.addEventListener("resize", update);
    update();

    if (!document.getElementById(styleId)) {
        const styleEl = document.createElement("style");
        styleEl.id = styleId;
        const parentStyle = main ? window.getComputedStyle(main) : null;
        const resolvedContainerCss = containerCss
            .replace(/__parent__\\.geometry\\.([a-zA-Z0-9_-]+)/g, (_, prop) => {
                return `var(--st-float-${ref}-${prop})`;
            })
            .replace(/__parent__\\.style\\.([a-zA-Z0-9_-]+)/g, (_, prop) => {
                if (!parentStyle) return "0px";
                const value = parentStyle.getPropertyValue(prop).trim();
                return value || "0px";
            })
            .replace(/__theme__\\.([a-zA-Z0-9_-]+)/g, (_, prop) => {
                return `var(--st-float-${ref}-theme-${prop})`;
            });
        const resolvedDocumentCss = documentCss.replaceAll("__child__", containerSelector);
        styleEl.textContent = `
${containerSelector} {
    ${resolvedContainerCss}
}
${floatSelector} {
    display: none !important;
    margin: 0 !important;
    padding: 0 !important;
    height: 0 !important;
    width: 0 !important;
    overflow: hidden !important;
    position: absolute !important;
    visibility: hidden !important;
}
${paddingBottom ? `div[data-testid="stAppViewContainer"] .main .block-container { padding-bottom: ${paddingBottom}; }` : ""}
${resolvedDocumentCss ? resolvedDocumentCss : ""}
`;
        document.head.appendChild(styleEl);
    }

    const container =
        (parentElement && parentElement.closest && parentElement.closest('[data-testid="stElementContainer"]')) ||
        (parentElement && parentElement.closest && parentElement.closest('[data-testid="stVerticalBlock"]')) ||
        (parentElement ? parentElement.parentElement : null);

    if (parentElement && parentElement.style) {
        Object.assign(parentElement.style, {
            display: "none",
            margin: "0",
            padding: "0",
            height: "0",
            width: "0",
            overflow: "hidden",
            position: "absolute",
            visibility: "hidden"
        });
    }
    if (container && container.style) {
        Object.assign(container.style, {
            display: "none",
            margin: "0",
            padding: "0",
            height: "0",
            width: "0",
            overflow: "hidden"
        });
    }
}
"""

# Register the marker component v2 once
def _marker_component(*args, **kwargs):
    component_key = state_key("float_marker_component")
    if component_key not in st.session_state:
        st.session_state[component_key] = v2_components.component(
            "float_marker",
            js=MARKER_JS,
        )
    return st.session_state[component_key](*args, **kwargs)

# Register the main component v2 once
def _component(*args, **kwargs):
    component_key = state_key("float_container_component")
    if component_key not in st.session_state:
        st.session_state[component_key] = v2_components.component(
            "floating_container",
            js=JS,
        )
    return st.session_state[component_key](*args, **kwargs)

def float_container(
    *,
    ref: str,
    container_css: str,
    document_css: str = "",
    padding_bottom: str | None = "7.5rem",
    alpha: float = 0.95,
) -> None:
    # Create the invisible marker using a v2 component
    _marker_component(
        data={"ref": ref},
        key=state_key(f"float_marker_{ref}"),
        isolate_styles=False,
    )

    container_css = textwrap.dedent(container_css).strip()
    document_css = textwrap.dedent(document_css).strip()
    _component(
        data={
            "ref": ref,
            "containerCss": container_css,
            "documentCss": document_css,
            "paddingBottom": padding_bottom or "",
            "alpha": alpha,
        },
        key=state_key(f"float_component_instance_{ref}"),
        isolate_styles=False,
    )