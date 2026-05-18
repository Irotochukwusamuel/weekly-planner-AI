from setuptools import setup, find_packages

setup(
    name="weekly_planner",
    version="1.0.0",
    description="A modular weekly schedule planner that learns from your feedback using ML",
    author="Iro Tochukwu Samuel",
    packages=find_packages(where="."),
    package_dir={"": "."},
    py_modules=["__main__"],
    python_requires=">=3.9",
    install_requires=[],
    extras_require={
        "ml": ["scikit-learn", "numpy"],
    },
    entry_points={
        "console_scripts": [
            "weekly-planner=main:main",
        ],
    },
)
