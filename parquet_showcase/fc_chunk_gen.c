#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <openssl/md5.h>

#ifdef _WIN32
#define EXPORT __declspec(dllexport)
#else
#define EXPORT
#endif

EXPORT void generate_csv_chunk(uint32_t start_pid, uint32_t end_pid, const char* filepath) {
    FILE* file = fopen(filepath, "w");
    if (!file) return;

    uint8_t buffer[8];
    memcpy(buffer + 4, "JCMR", 4);

    for (uint32_t pid = start_pid; pid < end_pid; pid++) {
        if (pid == 0) {
            fprintf(file, "000000000000,12\n");
            continue;
        }

        buffer[0] = (pid >> 0) & 0xFF;
        buffer[1] = (pid >> 8) & 0xFF;
        buffer[2] = (pid >> 16) & 0xFF;
        buffer[3] = (pid >> 24) & 0xFF;

        uint8_t digest[MD5_DIGEST_LENGTH];
        MD5(buffer, 8, digest);

        uint64_t high = digest[0] >> 1;
        uint64_t full_fc_int = (high << 32) | pid;

        char fc_str[13];
        snprintf(fc_str, sizeof(fc_str), "%012llu", (unsigned long long)full_fc_int);

        uint64_t mask = 0;
        int counts[10] = {0};
        for (int i = 0; i < 12; i++) {
            counts[fc_str[i] - '0']++;
        }
        for (int digit = 0; digit < 10; digit++) {
            mask |= ((uint64_t)counts[digit] << (digit * 4));
        }

        fprintf(file, "%s,%llu\n", fc_str, mask);
    }

    fclose(file);
}