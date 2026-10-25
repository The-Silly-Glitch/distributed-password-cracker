#pragma once
#include <cuda_runtime.h>
#include <cstdint>

#define MD5_F(x, y, z) (((x) & (y)) | ((~x) & (z)))
#define MD5_G(x, y, z) (((x) & (z)) | ((y) & (~z)))
#define MD5_H(x, y, z) ((x) ^ (y) ^ (z))
#define MD5_I(x, y, z) ((y) ^ ((x) | (~z)))

#define MD5_ROTL(a, b) (((a) << (b)) | ((a) >> (32 - (b))))

#define MD5_FF(a, b, c, d, x, s, ac) { \
    (a) += MD5_F((b), (c), (d)) + (x) + (uint32_t)(ac); \
    (a) = MD5_ROTL((a), (s)); \
    (a) += (b); \
}
#define MD5_GG(a, b, c, d, x, s, ac) { \
    (a) += MD5_G((b), (c), (d)) + (x) + (uint32_t)(ac); \
    (a) = MD5_ROTL((a), (s)); \
    (a) += (b); \
}
#define MD5_HH(a, b, c, d, x, s, ac) { \
    (a) += MD5_H((b), (c), (d)) + (x) + (uint32_t)(ac); \
    (a) = MD5_ROTL((a), (s)); \
    (a) += (b); \
}
#define MD5_II(a, b, c, d, x, s, ac) { \
    (a) += MD5_I((b), (c), (d)) + (x) + (uint32_t)(ac); \
    (a) = MD5_ROTL((a), (s)); \
    (a) += (b); \
}

__device__ __forceinline__ void md5_process_block(uint32_t state[4], const uint32_t block[16]) {
    uint32_t a = state[0], b = state[1], c = state[2], d = state[3];

    // Round 1
    MD5_FF(a, b, c, d, block[0], 7, 0xd76aa478);
    MD5_FF(d, a, b, c, block[1], 12, 0xe8c7b756);
    MD5_FF(c, d, a, b, block[2], 17, 0x242070db);
    MD5_FF(b, c, d, a, block[3], 22, 0xc1bdceee);
    MD5_FF(a, b, c, d, block[4], 7, 0xf57c0faf);
    MD5_FF(d, a, b, c, block[5], 12, 0x4787c62a);
    MD5_FF(c, d, a, b, block[6], 17, 0xa8304613);
    MD5_FF(b, c, d, a, block[7], 22, 0xfd469501);
    MD5_FF(a, b, c, d, block[8], 7, 0x698098d8);
    MD5_FF(d, a, b, c, block[9], 12, 0x8b44f7af);
    MD5_FF(c, d, a, b, block[10], 17, 0xffff5bb1);
    MD5_FF(b, c, d, a, block[11], 22, 0x895cd7be);
    MD5_FF(a, b, c, d, block[12], 7, 0x6b901122);
    MD5_FF(d, a, b, c, block[13], 12, 0xfd987193);
    MD5_FF(c, d, a, b, block[14], 17, 0xa679438e);
    MD5_FF(b, c, d, a, block[15], 22, 0x49b40821);

    // Round 2
    MD5_GG(a, b, c, d, block[1], 5, 0xf61e2562);
    MD5_GG(d, a, b, c, block[6], 9, 0xc040b340);
    MD5_GG(c, d, a, b, block[11], 14, 0x265e5a51);
    MD5_GG(b, c, d, a, block[0], 20, 0xe9b6c7aa);
    MD5_GG(a, b, c, d, block[5], 5, 0xd62f105d);
    MD5_GG(d, a, b, c, block[10], 9, 0x02441453);
    MD5_GG(c, d, a, b, block[15], 14, 0xd8a1e681);
    MD5_GG(b, c, d, a, block[4], 20, 0xe7d3fbc8);
    MD5_GG(a, b, c, d, block[9], 5, 0x21e1cde6);
    MD5_GG(d, a, b, c, block[14], 9, 0xc33707d6);
    MD5_GG(c, d, a, b, block[3], 14, 0xf4d50d87);
    MD5_GG(b, c, d, a, block[8], 20, 0x455a14ed);
    MD5_GG(a, b, c, d, block[13], 5, 0xa9e3e905);
    MD5_GG(d, a, b, c, block[2], 9, 0xfcefa3f8);
    MD5_GG(c, d, a, b, block[7], 14, 0x676f02d9);
    MD5_GG(b, c, d, a, block[12], 20, 0x8d2a4c8a);

    // Round 3
    MD5_HH(a, b, c, d, block[5], 4, 0xfffa3942);
    MD5_HH(d, a, b, c, block[8], 11, 0x8771f681);
    MD5_HH(c, d, a, b, block[11], 16, 0x6d9d6122);
    MD5_HH(b, c, d, a, block[14], 23, 0xfde5380c);
    MD5_HH(a, b, c, d, block[1], 4, 0xa4beea44);
    MD5_HH(d, a, b, c, block[4], 11, 0x4bdecfa9);
    MD5_HH(c, d, a, b, block[7], 16, 0xf6bb4b60);
    MD5_HH(b, c, d, a, block[10], 23, 0xbebfbc70);
    MD5_HH(a, b, c, d, block[13], 4, 0x289b7ec6);
    MD5_HH(d, a, b, c, block[0], 11, 0xeaa127fa);
    MD5_HH(c, d, a, b, block[3], 16, 0xd4ef3085);
    MD5_HH(b, c, d, a, block[6], 23, 0x04881d05);
    MD5_HH(a, b, c, d, block[9], 4, 0xd9d4d039);
    MD5_HH(d, a, b, c, block[12], 11, 0xe6db99e5);
    MD5_HH(c, d, a, b, block[15], 16, 0x1fa27cf8);
    MD5_HH(b, c, d, a, block[2], 23, 0xc4ac5665);

    // Round 4
    MD5_II(a, b, c, d, block[0], 6, 0xf4292244);
    MD5_II(d, a, b, c, block[7], 10, 0x432aff97);
    MD5_II(c, d, a, b, block[14], 15, 0xab9423a7);
    MD5_II(b, c, d, a, block[5], 21, 0xfc93a039);
    MD5_II(a, b, c, d, block[12], 6, 0x655b59c3);
    MD5_II(d, a, b, c, block[3], 10, 0x8f0ccc92);
    MD5_II(c, d, a, b, block[10], 15, 0xffeff47d);
    MD5_II(b, c, d, a, block[1], 21, 0x85845dd1);
    MD5_II(a, b, c, d, block[8], 6, 0x6fa87e4f);
    MD5_II(d, a, b, c, block[15], 10, 0xfe2ce6e0);
    MD5_II(c, d, a, b, block[6], 15, 0xa3014314);
    MD5_II(b, c, d, a, block[13], 21, 0x4e0811a1);
    MD5_II(a, b, c, d, block[4], 6, 0xf7537e82);
    MD5_II(d, a, b, c, block[11], 10, 0xbd3af235);
    MD5_II(c, d, a, b, block[2], 15, 0x2ad7d2bb);
    MD5_II(b, c, d, a, block[9], 21, 0xeb86d391);

    state[0] += a;
    state[1] += b;
    state[2] += c;
    state[3] += d;
}

__device__ __forceinline__ void md5_hash(const uint8_t* msg, uint32_t len, char* hex_out) {
    uint32_t state[4] = { 0x67452301, 0xefcdab89, 0x98badcfe, 0x10325476 };
    
    // Support messages up to 119 bytes (fits in 1 or 2 blocks of 64 bytes)
    uint32_t num_blocks = (len + 8 >= 64) ? 2 : 1;
    uint8_t buf[128] = { 0 };

    for (uint32_t i = 0; i < len; ++i) {
        buf[i] = msg[i];
    }
    buf[len] = 0x80;

    // Bit length in last 8 bytes of the final block (little-endian)
    uint64_t bit_len = (uint64_t)len * 8ULL;
    uint32_t total_buf_len = num_blocks * 64;
    buf[total_buf_len - 8] = (uint8_t)(bit_len & 0xff);
    buf[total_buf_len - 7] = (uint8_t)((bit_len >> 8) & 0xff);
    buf[total_buf_len - 6] = (uint8_t)((bit_len >> 16) & 0xff);
    buf[total_buf_len - 5] = (uint8_t)((bit_len >> 24) & 0xff);
    buf[total_buf_len - 4] = (uint8_t)((bit_len >> 32) & 0xff);
    buf[total_buf_len - 3] = (uint8_t)((bit_len >> 40) & 0xff);
    buf[total_buf_len - 2] = (uint8_t)((bit_len >> 48) & 0xff);
    buf[total_buf_len - 1] = (uint8_t)((bit_len >> 56) & 0xff);

    for (uint32_t b = 0; b < num_blocks; ++b) {
        uint32_t M[16];
        const uint8_t* bptr = buf + b * 64;
        for (int i = 0; i < 16; ++i) {
            M[i] = ((uint32_t)bptr[i*4]) |
                   (((uint32_t)bptr[i*4 + 1]) << 8) |
                   (((uint32_t)bptr[i*4 + 2]) << 16) |
                   (((uint32_t)bptr[i*4 + 3]) << 24);
        }
        md5_process_block(state, M);
    }

    const char hex_chars[] = "0123456789abcdef";
    for (int i = 0; i < 4; ++i) {
        uint32_t val = state[i];
        for (int j = 0; j < 4; ++j) {
            uint8_t byte = (uint8_t)((val >> (j * 8)) & 0xff);
            hex_out[(i * 4 + j) * 2]     = hex_chars[(byte >> 4) & 0x0f];
            hex_out[(i * 4 + j) * 2 + 1] = hex_chars[byte & 0x0f];
        }
    }
    hex_out[32] = '\0';
}
