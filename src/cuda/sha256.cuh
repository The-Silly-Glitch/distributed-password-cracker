#pragma once
#include <cuda_runtime.h>
#include <cstdint>

#define SHA256_ROTR(a, b) (((a) >> (b)) | ((a) << (32 - (b))))
#define SHA256_CH(x, y, z) (((x) & (y)) ^ ((~(x)) & (z)))
#define SHA256_MAJ(x, y, z) (((x) & (y)) ^ ((x) & (z)) ^ ((y) & (z)))
#define SHA256_EP0(x) (SHA256_ROTR(x, 2) ^ SHA256_ROTR(x, 13) ^ SHA256_ROTR(x, 22))
#define SHA256_EP1(x) (SHA256_ROTR(x, 6) ^ SHA256_ROTR(x, 11) ^ SHA256_ROTR(x, 25))
#define SHA256_SIG0(x) (SHA256_ROTR(x, 7) ^ SHA256_ROTR(x, 18) ^ ((x) >> 3))
#define SHA256_SIG1(x) (SHA256_ROTR(x, 17) ^ SHA256_ROTR(x, 19) ^ ((x) >> 10))

__constant__ const uint32_t SHA256_K[64] = {
    0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
    0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
    0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
    0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
    0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
    0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
    0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
    0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2
};

__device__ __forceinline__ void sha256_process_block(uint32_t state[8], const uint32_t W_in[16]) {
    uint32_t W[64];
    for (int i = 0; i < 16; ++i) {
        W[i] = W_in[i];
    }
    for (int i = 16; i < 64; ++i) {
        W[i] = SHA256_SIG1(W[i - 2]) + W[i - 7] + SHA256_SIG0(W[i - 15]) + W[i - 16];
    }

    uint32_t a = state[0], b = state[1], c = state[2], d = state[3];
    uint32_t e = state[4], f = state[5], g = state[6], h = state[7];

    for (int t = 0; t < 64; ++t) {
        uint32_t t1 = h + SHA256_EP1(e) + SHA256_CH(e, f, g) + SHA256_K[t] + W[t];
        uint32_t t2 = SHA256_EP0(a) + SHA256_MAJ(a, b, c);
        h = g;
        g = f;
        f = e;
        e = d + t1;
        d = c;
        c = b;
        b = a;
        a = t1 + t2;
    }

    state[0] += a;
    state[1] += b;
    state[2] += c;
    state[3] += d;
    state[4] += e;
    state[5] += f;
    state[6] += g;
    state[7] += h;
}

__device__ __forceinline__ void sha256_hash(const uint8_t* msg, uint32_t len, char* hex_out) {
    uint32_t state[8] = {
        0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a,
        0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19
    };

    uint32_t num_blocks = (len + 8 >= 64) ? 2 : 1;
    uint8_t buf[128] = { 0 };

    for (uint32_t i = 0; i < len; ++i) {
        buf[i] = msg[i];
    }
    buf[len] = 0x80;

    uint64_t bit_len = (uint64_t)len * 8ULL;
    uint32_t total_buf_len = num_blocks * 64;
    for (int i = 0; i < 8; ++i) {
        buf[total_buf_len - 1 - i] = (uint8_t)((bit_len >> (i * 8)) & 0xff);
    }

    for (uint32_t b = 0; b < num_blocks; ++b) {
        uint32_t W[16];
        const uint8_t* bptr = buf + b * 64;
        for (int i = 0; i < 16; ++i) {
            W[i] = (((uint32_t)bptr[i * 4]) << 24) |
                   (((uint32_t)bptr[i * 4 + 1]) << 16) |
                   (((uint32_t)bptr[i * 4 + 2]) << 8) |
                   (((uint32_t)bptr[i * 4 + 3]));
        }
        sha256_process_block(state, W);
    }

    const char hex_chars[] = "0123456789abcdef";
    for (int i = 0; i < 8; ++i) {
        uint32_t val = state[i];
        for (int j = 0; j < 4; ++j) {
            uint8_t byte = (uint8_t)((val >> ((3 - j) * 8)) & 0xff);
            hex_out[(i * 4 + j) * 2]     = hex_chars[(byte >> 4) & 0x0f];
            hex_out[(i * 4 + j) * 2 + 1] = hex_chars[byte & 0x0f];
        }
    }
    hex_out[64] = '\0';
}
