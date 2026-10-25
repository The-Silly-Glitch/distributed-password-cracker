import os
import sys
import shutil
import subprocess
import sysconfig
from setuptools import setup, Extension, find_packages
from setuptools.command.build_ext import build_ext


def find_nvcc():
    cuda_home = os.environ.get("CUDA_HOME")
    candidates = []
    if cuda_home:
        candidates.append(os.path.join(cuda_home, "bin", "nvcc"))
    candidates.extend([
        "/usr/local/cuda-13.2/bin/nvcc",
        "/usr/local/cuda/bin/nvcc",
        "/usr/local/cuda-13/bin/nvcc",
        "/usr/local/cuda-12/bin/nvcc",
        shutil.which("nvcc") or ""
    ])
    for cand in candidates:
        if cand and os.path.exists(cand) and os.access(cand, os.X_OK):
            return cand
    return None


class BuildCUDAExt(build_ext):
    def build_extension(self, ext):
        import pybind11

        nvcc = find_nvcc()
        if not nvcc:
            raise RuntimeError("CUDA nvcc compiler not found. Ensure CUDA toolkit is installed.")

        out_path = self.get_ext_fullpath(ext.name)
        os.makedirs(os.path.dirname(out_path), exist_ok=True)

        py_inc = sysconfig.get_path("include")
        pybind11_inc = pybind11.get_include()
        cuda_src_dir = os.path.abspath("src/cuda")

        sources = [os.path.abspath(s) for s in ext.sources]

        # Determine architecture flags (Ada Lovelace RTX 4050 uses sm_89)
        arch_flags = ["-arch=sm_89"]

        cmd = [
            nvcc,
            "-shared",
            "-std=c++17",
            "-O3",
            "-Xcompiler", "-fPIC",
            f"-I{py_inc}",
            f"-I{pybind11_inc}",
            f"-I{cuda_src_dir}",
            *arch_flags,
            *sources,
            "-o", out_path
        ]

        print("Compiling CUDA extension:", " ".join(cmd))
        subprocess.check_call(cmd)

    def run(self):
        super().run()
        if self.inplace:
            for ext in self.extensions:
                fullname = self.get_ext_filename(ext.name)
                src_path = os.path.join(self.build_lib, fullname)
                if not os.path.exists(src_path):
                    src_path = os.path.join("src", fullname)
                if os.path.exists(src_path):
                    root_target = os.path.abspath(fullname)
                    src_target = os.path.abspath(os.path.join("src", fullname))
                    if os.path.abspath(src_path) != root_target:
                        shutil.copyfile(src_path, root_target)
                    if os.path.abspath(src_path) != src_target:
                        shutil.copyfile(src_path, src_target)


cuda_module = Extension(
    name="crack_gpu",
    sources=[
        "src/cuda/crack_gpu.cu",
        "src/cuda/bindings.cpp"
    ]
)

setup(
    name="distributed-password-cracker",
    version="0.1.0",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    ext_modules=[cuda_module],
    cmdclass={"build_ext": BuildCUDAExt},
    package_data={
        "crack_core": ["wordlists/*.txt"],
        "crack_dashboard": ["templates/*", "static/*"]
    },
    include_package_data=True,
    python_requires=">=3.10",
)
