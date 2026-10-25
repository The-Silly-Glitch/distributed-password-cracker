#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include "kernels.cuh"

namespace py = pybind11;

PYBIND11_MODULE(crack_gpu, m) {
    m.doc() = "GPU-accelerated password candidate hashing using CUDA";

    m.def("hash_batch", &cuda_hash_batch, 
          py::arg("algorithm"), 
          py::arg("candidates"), 
          py::arg("salt") = "",
          "Compute batch hashes for candidates on the GPU (algorithm: md5, sha1, sha256, bcrypt)");

    m.def("get_device_count", &cuda_get_device_count, "Return number of available CUDA devices");

    m.def("get_device_name", &cuda_get_device_name, 
          py::arg("device_id") = 0, 
          "Return the name of the CUDA device");

    m.def("is_cuda_available", []() -> bool {
        return cuda_get_device_count() > 0;
    }, "Check if CUDA runtime and compatible GPU are available");
}
