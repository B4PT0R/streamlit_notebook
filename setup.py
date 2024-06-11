import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="streamlit_notebook",
    version="0.0.11",
    author="Baptiste Ferrand",
    author_email="bferrand.maths@gmail.com",
    description="A notebook interface for Streamlit.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/B4PT0R/streamlit_notebook",
    packages=setuptools.find_packages(),
        package_data={
        'streamlit_notebook': [
            'app_images/*',
            'demo_notebooks/*',
            'launch_app.py'
        ]
    },
    entry_points={
        'console_scripts': [
            'st_notebook=streamlit_notebook.launch_app:main',
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    install_requires=[
        "streamlit-code-editor==0.1.20",
        "streamlit>=1.35.0",
        "matplotlib",
        "numpy",
        "seaborn",
        "pandas",
        "graphviz",
        "altair",
        "plotly",
        "bokeh",
        "pydeck",
        "scipy",
        "sympy",
        "scikit-learn",
        "vega-datasets"
    ],
    python_requires='>=3.9',
)
