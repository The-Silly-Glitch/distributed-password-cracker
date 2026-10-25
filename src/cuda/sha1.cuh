#pragma once
#include <cuda_runtime.h>
#include <cstdint>

#define SHA1_ROTL(a, b) (((a) << (b)) | ((a) >> (32 - (b))))

__device__ __forceinline__ void sha1_process_block(uint32_t state[5], const uint32_t W_in[16]) {
    uint32_t W[80];
    for (int i = 0; i < 16; ++i) {
        W[i] = W_in[i];
    }
    for (int i = 16; i < 80; ++i) {
        W[i] = SHA1_ROTL(W[i - 3] ^ W[i - 8] ^ W[i - 14] ^ W[i - 16], 1);
    }

    uint32_t a = state[0], b = state[1], c = state[2], d = state[3], e = state[4];

    for (int t = 0; t < 80; ++t) {
        uint32_t f, k;
        if (t < 20) {
            f = (b & c) | ((~b) & d);
            k = 0x5A827999;
        } else if (t < 40) {
            f = b ^ c ^ d;
            k = 0x6ED9EBA1;
        } else if (t < 60) {
            f = (b & c) | (b & d) | (c & d);
            k = 0x8F1BBCDC;
        } else {
            f = b ^ c ^ d;
            k = 0xCA62C1D6;
        }

        uint32_t temp = SHA1_ROTL(a, 5) + f + e + k + W[t];
        e = d;
        d = c;
        c = SHA1_ROTL(b, 30);
        b = a;
        a = temp;
    }

    state[0] += a;
    state[1] += b;
    state[2] += c;
    state[3] += d;
    state[4] += e;
}

__device__ __forceinline__ void sha1_hash(const uint8_t* msg, uint32_t len, char* hex_out) {
    uint32_t state[5] = { 0x67452301, 0xEFCDAB89, 0x98BADCFE, 0x10325476, 0xC3D2E1F0 };

    uint32_t num_blocks = (len + 8 >= 64) ? 2 : 1;
    uint8_t buf[128] = { 0 };

    for (uint32_t i = 0; i < len; ++i) {
        buf[i] = msg[i];
    }
    buf[len] = 0x80;

    // Bit length big-endian
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
        sha1_process_block(state, W);
    }

    const char hex_chars[] = "0123456789abcdef";
    for (int i = 0; i < 5; ++i) {
        uint32_t val = state[i];
        for (int j = 0; j < 4; ++j) {
            uint8_t byte = (uint8_t)((val >> ((3 - j) * 8)) & 0xff);
            hex_out[(i * 4 + j) * 2]     = hex_chars[(byte >> 4) & 0x0f];
            hex_out[(i * 4 + j) * 2 + 1] = hex_chars[byte & 0x0f];
        }
    }
    hex_out[40] = '\0';
}
