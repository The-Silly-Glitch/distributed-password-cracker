#pragma once
#include <cuda_runtime.h>
#include <string>
#include <vector>
#include "md5.cuh"
#include "sha1.cuh"
#include "sha256.cuh"
#include "bcrypt.cuh"

#define MAX_CANDIDATE_LEN 64
#define RESULT_STRIDE 128

enum AlgorithmType {
    ALGO_MD5 = 0,
    ALGO_SHA1 = 1,
    ALGO_SHA256 = 2,
    ALGO_BCRYPT = 3
};

__global__ void md5_batch_kernel(const uint8_t* candidates, const uint32_t* lengths, char* out, uint32_t count);
__global__ void sha1_batch_kernel(const uint8_t* candidates, const uint32_t* lengths, char* out, uint32_t count);
__global__ void sha256_batch_kernel(const uint8_t* candidates, const uint32_t* lengths, char* out, uint32_t count);
__global__ void bcrypt_batch_kernel(const uint8_t* candidates, const uint32_t* lengths, const char* salt, char* out, uint32_t count);

std::vector<std::string> cuda_hash_batch(const std::string& algorithm, const std::vector<std::string>& candidates, const std::string& salt = "");
int cuda_get_device_count();
std::string cuda_get_device_name(int device_id = 0);
