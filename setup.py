from setuptools import Extension, find_packages, setup

speedups_ext = Extension(
    "edcode._speedups",
    sources=["edcode/_speedups.c"],
    optional=True,
)

if __name__ == "__main__":
    setup(
        packages=find_packages(),
        ext_modules=[speedups_ext],
    )
