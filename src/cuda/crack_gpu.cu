#include "kernels.cuh"
#include <iostream>
#include <algorithm>
#include <cstring>
#include <stdexcept>

__global__ void md5_batch_kernel(const uint8_t* candidates, const uint32_t* lengths, char* out, uint32_t count) {
    uint32_t idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx >= count) return;

    const uint8_t* cand = candidates + (idx * MAX_CANDIDATE_LEN);
    uint32_t len = lengths[idx];
    char* res = out + (idx * RESULT_STRIDE);

    md5_hash(cand, len, res);
}

__global__ void sha1_batch_kernel(const uint8_t* candidates, const uint32_t* lengths, char* out, uint32_t count) {
    uint32_t idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx >= count) return;

    const uint8_t* cand = candidates + (idx * MAX_CANDIDATE_LEN);
    uint32_t len = lengths[idx];
    char* res = out + (idx * RESULT_STRIDE);

    sha1_hash(cand, len, res);
}

__global__ void sha256_batch_kernel(const uint8_t* candidates, const uint32_t* lengths, char* out, uint32_t count) {
    uint32_t idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx >= count) return;

    const uint8_t* cand = candidates + (idx * MAX_CANDIDATE_LEN);
    uint32_t len = lengths[idx];
    char* res = out + (idx * RESULT_STRIDE);

    sha256_hash(cand, len, res);
}

__global__ void bcrypt_batch_kernel(const uint8_t* candidates, const uint32_t* lengths, const char* salt, char* out, uint32_t count) {
    uint32_t idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx >= count) return;

    const uint8_t* cand = candidates + (idx * MAX_CANDIDATE_LEN);
    uint32_t len = lengths[idx];
    char* res = out + (idx * RESULT_STRIDE);

    bcrypt_hash_candidate(cand, len, salt, res);
}

int cuda_get_device_count() {
    int count = 0;
    cudaError_t err = cudaGetDeviceCount(&count);
    if (err != cudaSuccess) return 0;
    return count;
}

std::string cuda_get_device_name(int device_id) {
    int count = cuda_get_device_count();
    if (count == 0 || device_id >= count) return "No CUDA Device";
    cudaDeviceProp prop;
    cudaGetDeviceProperties(&prop, device_id);
    return std::string(prop.name);
}

std::vector<std::string> cuda_hash_batch(const std::string& algorithm, const std::vector<std::string>& candidates, const std::string& salt) {
    uint32_t count = static_cast<uint32_t>(candidates.size());
    if (count == 0) {
        return {};
    }

    std::string algo = algorithm;
    std::transform(algo.begin(), algo.end(), algo.begin(), ::tolower);

    // Prepare host contiguous buffers
    size_t cand_buf_size = static_cast<size_t>(count) * MAX_CANDIDATE_LEN;
    size_t len_buf_size = static_cast<size_t>(count) * sizeof(uint32_t);
    size_t res_buf_size = static_cast<size_t>(count) * RESULT_STRIDE;

    std::vector<uint8_t> h_cand(cand_buf_size, 0);
    std::vector<uint32_t> h_lens(count, 0);

    for (uint32_t i = 0; i < count; ++i) {
        const std::string& s = candidates[i];
        uint32_t len = static_cast<uint32_t>(s.size());
        if (len > MAX_CANDIDATE_LEN - 1) {
            len = MAX_CANDIDATE_LEN - 1;
        }
        h_lens[i] = len;
        std::memcpy(h_cand.data() + (i * MAX_CANDIDATE_LEN), s.data(), len);
    }

    uint8_t* d_candidates = nullptr;
    uint32_t* d_lengths = nullptr;
    char* d_out = nullptr;
    char* d_salt = nullptr;

    cudaError_t err;
    err = cudaMalloc(&d_candidates, cand_buf_size);
    if (err != cudaSuccess) throw std::runtime_error(std::string("CUDA Malloc failed: ") + cudaGetErrorString(err));

    err = cudaMalloc(&d_lengths, len_buf_size);
    if (err != cudaSuccess) {
        cudaFree(d_candidates);
        throw std::runtime_error(std::string("CUDA Malloc failed: ") + cudaGetErrorString(err));
    }

    err = cudaMalloc(&d_out, res_buf_size);
    if (err != cudaSuccess) {
        cudaFree(d_candidates);
        cudaFree(d_lengths);
        throw std::runtime_error(std::string("CUDA Malloc failed: ") + cudaGetErrorString(err));
    }

    // Host to Device Memcpy
    cudaMemcpy(d_candidates, h_cand.data(), cand_buf_size, cudaMemcpyHostToDevice);
    cudaMemcpy(d_lengths, h_lens.data(), len_buf_size, cudaMemcpyHostToDevice);

    // Launch configuration
    int threads_per_block = (algo == "bcrypt") ? 64 : 256;
    int blocks = (count + threads_per_block - 1) / threads_per_block;

    if (algo == "md5") {
        md5_batch_kernel<<<blocks, threads_per_block>>>(d_candidates, d_lengths, d_out, count);
    } else if (algo == "sha1") {
        sha1_batch_kernel<<<blocks, threads_per_block>>>(d_candidates, d_lengths, d_out, count);
    } else if (algo == "sha256") {
        sha256_batch_kernel<<<blocks, threads_per_block>>>(d_candidates, d_lengths, d_out, count);
    } else if (algo == "bcrypt") {
        size_t salt_len = salt.size() + 1;
        cudaMalloc(&d_salt, salt_len);
        cudaMemcpy(d_salt, salt.c_str(), salt_len, cudaMemcpyHostToDevice);
        bcrypt_batch_kernel<<<blocks, threads_per_block>>>(d_candidates, d_lengths, d_salt, d_out, count);
    } else {
        cudaFree(d_candidates);
        cudaFree(d_lengths);
        cudaFree(d_out);
        throw std::invalid_argument("Unsupported algorithm: " + algorithm);
    }

    cudaDeviceSynchronize();
    err = cudaGetLastError();
    if (err != cudaSuccess) {
        cudaFree(d_candidates);
        cudaFree(d_lengths);
        cudaFree(d_out);
        if (d_salt) cudaFree(d_salt);
        throw std::runtime_error(std::string("CUDA Kernel error: ") + cudaGetErrorString(err));
    }

    // Device to Host Memcpy
    std::vector<char> h_res(res_buf_size, 0);
    cudaMemcpy(h_res.data(), d_out, res_buf_size, cudaMemcpyDeviceToHost);

    // Free GPU buffers
    cudaFree(d_candidates);
    cudaFree(d_lengths);
    cudaFree(d_out);
    if (d_salt) cudaFree(d_salt);

    // Format output strings
    std::vector<std::string> results;
    results.reserve(count);
    for (uint32_t i = 0; i < count; ++i) {
        const char* ptr = h_res.data() + (i * RESULT_STRIDE);
        results.emplace_back(ptr);
    }

    return results;
}
