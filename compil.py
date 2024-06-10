import os
import pathlib

def compile_python_files(output_filename="all.txt"):
    # Utiliser le module pathlib pour naviguer dans les fichiers et dossiers
    base_path = pathlib.Path('.')
    with open(output_filename, "w", encoding="utf-8") as outfile:
        # Parcourir tous les fichiers .py dans le répertoire courant et les sous-dossiers
        for filepath in base_path.rglob('*.py'):
            # Ignorer les fichiers dans les répertoires 'build', 'dist', et '__pycache__'
            if 'build' in filepath.parts or 'dist' in filepath.parts or '__pycache__' in filepath.parts:
                continue
            with open(filepath, "r", encoding="utf-8") as infile:
                # Écrire le nom du fichier avec un chemin relatif par rapport à base_path
                outfile.write(f"### {filepath.relative_to(base_path)}\n")
                outfile.write(infile.read())
                outfile.write("\n\n")


if __name__ == "__main__":
    compile_python_files()