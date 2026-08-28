#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define PE_SIGNATURE_32BIT 0x45504C45 // "PE\0"
#define PE_SIGNATURE_64BIT 0x45505348 // "PE\0x86"

void check_pe_signature(const unsigned char *data) {
    unsigned char signature[4];
    memcpy(signature, data, 4);

    if (memcmp(signature, PE_SIGNATURE_32BIT, 4) == 0) {
        printf("PE (32-bit)\n");
    } else if (memcmp(signature, PE_SIGNATURE_64BIT, 4) == 0) {
        printf("PE32+\n");
    } else {
        printf("Unknown PE signature\n");
    }
}



unsigned char *load_file(const char *file_path) {
    FILE *file = fopen(file_path, "rb");
    if (file == NULL) {
        return NULL;
    }

    fseek(file, 0, SEEK_END);
    size_t file_size = ftell(file);
    fseek(file, 0, SEEK_SET);

    unsigned char *data = (unsigned char *)malloc(file_size);
    if (data == NULL) {
        fclose(file);
        return NULL;
    }

    size_t bytes_read = fread(data, 1, file_size, file);
    if (bytes_read != file_size) {
        free(data);
        fclose(file);
        return NULL;
    }

    fclose(file);
    return data;
}

// Placeholder for your main function
int main(int argc, char *argv[]) {
    if (argc < 2) {
        fprintf(stderr, "Usage: %s <filename>\n", argv[0]);
        return EXIT_FAILURE;
    }

    const char *filename = argv[1];
    // Add your code to process the file
    unsigned char *file_data = load_file(filename);

    // Check the PE signature
    check_pe_signature(file_data);

    // Free the loaded file data
    free(file_data);

    return EXIT_SUCCESS;
}