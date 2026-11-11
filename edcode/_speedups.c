#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <stdint.h>
#include <string.h>

static PyObject *BinasciiError = NULL;

static const char B32_STD_ALPHABET[33] = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567";
static const char B32_HEX_ALPHABET[33] = "0123456789ABCDEFGHIJKLMNOPQRSTUV";

static const char B85_ALPHABET[86] =
    "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz!#$%&()*+-;<=>?@^_`{|}~";

static const char Z85_ALPHABET[86] =
    "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ.-:+=^!/*?&<>()[]{}@%$#";

/* ========================================================================= */
/* Base32 Core Helpers                                                       */
/* ========================================================================= */
static PyObject* do_b32encode(const unsigned char *in, Py_ssize_t in_len, const char *alphabet) {
    if (in_len == 0) {
        return PyBytes_FromStringAndSize("", 0);
    }

    Py_ssize_t out_len = ((in_len + 4) / 5) * 8;
    PyObject *out_obj = PyBytes_FromStringAndSize(NULL, out_len);
    if (!out_obj) {
        return NULL;
    }
    char *out = PyBytes_AS_STRING(out_obj);

    Py_ssize_t i = 0, j = 0;
    while (i + 5 <= in_len) {
        uint64_t c = ((uint64_t)in[i] << 32) |
                     ((uint64_t)in[i+1] << 24) |
                     ((uint64_t)in[i+2] << 16) |
                     ((uint64_t)in[i+3] << 8) |
                     ((uint64_t)in[i+4]);
        out[j]   = alphabet[(c >> 35) & 0x1F];
        out[j+1] = alphabet[(c >> 30) & 0x1F];
        out[j+2] = alphabet[(c >> 25) & 0x1F];
        out[j+3] = alphabet[(c >> 20) & 0x1F];
        out[j+4] = alphabet[(c >> 15) & 0x1F];
        out[j+5] = alphabet[(c >> 10) & 0x1F];
        out[j+6] = alphabet[(c >> 5) & 0x1F];
        out[j+7] = alphabet[c & 0x1F];
        i += 5;
        j += 8;
    }
    int leftover = (int)(in_len - i);
    if (leftover > 0) {
        uint64_t c = 0;
        for (int k = 0; k < leftover; k++) {
            c |= ((uint64_t)in[i + k]) << (32 - k * 8);
        }
        memset(out + j, '=', 8);
        out[j]   = alphabet[(c >> 35) & 0x1F];
        out[j+1] = alphabet[(c >> 30) & 0x1F];
        if (leftover >= 2) {
            out[j+2] = alphabet[(c >> 25) & 0x1F];
            out[j+3] = alphabet[(c >> 20) & 0x1F];
        }
        if (leftover >= 3) {
            out[j+4] = alphabet[(c >> 15) & 0x1F];
        }
        if (leftover >= 4) {
            out[j+5] = alphabet[(c >> 10) & 0x1F];
            out[j+6] = alphabet[(c >> 5) & 0x1F];
        }
    }
    return out_obj;
}

static PyObject* do_b32decode(const unsigned char *in, Py_ssize_t in_len, const char *alphabet,
                              int casefold, PyObject *map01_obj) {
    if (in_len == 0) {
        return PyBytes_FromStringAndSize("", 0);
    }

    if (in_len % 8 != 0) {
        PyErr_SetString(BinasciiError, "Incorrect padding");
        return NULL;
    }

    /* Build decode table */
    int16_t rev[256];
    memset(rev, -1, sizeof(rev));
    for (int k = 0; k < 32; k++) {
        rev[(unsigned char)alphabet[k]] = (int16_t)k;
    }
    if (casefold) {
        for (int k = 0; k < 32; k++) {
            unsigned char c = (unsigned char)alphabet[k];
            if (c >= 'A' && c <= 'Z') rev[c + 32] = (int16_t)k;
            else if (c >= 'a' && c <= 'z') rev[c - 32] = (int16_t)k;
        }
    }
    if (map01_obj && map01_obj != Py_None) {
        Py_buffer mview;
        if (PyObject_GetBuffer(map01_obj, &mview, PyBUF_SIMPLE) == 0) {
            if (mview.len == 1) {
                unsigned char m = ((unsigned char*)mview.buf)[0];
                rev['0'] = rev['O'];
                if (casefold) rev['o'] = rev['O'];
                rev['1'] = rev[m];
                if (casefold) {
                    if (m >= 'A' && m <= 'Z') rev['1'] = rev[m + 32] != -1 ? rev[m + 32] : rev[m];
                    else if (m >= 'a' && m <= 'z') rev['1'] = rev[m - 32] != -1 ? rev[m - 32] : rev[m];
                }
            }
            PyBuffer_Release(&mview);
        }
    }

    /* Check padding characters at end */
    Py_ssize_t padchars = 0;
    while (padchars < in_len && in[in_len - 1 - padchars] == '=') {
        padchars++;
    }
    if (padchars != 0 && padchars != 1 && padchars != 3 && padchars != 4 && padchars != 6) {
        PyErr_SetString(BinasciiError, "Incorrect padding");
        return NULL;
    }

    Py_ssize_t full_quanta = in_len / 8;
    Py_ssize_t out_len = full_quanta * 5;
    if (padchars == 1) out_len -= 1;
    else if (padchars == 3) out_len -= 2;
    else if (padchars == 4) out_len -= 3;
    else if (padchars == 6) out_len -= 4;

    PyObject *out_obj = PyBytes_FromStringAndSize(NULL, out_len);
    if (!out_obj) {
        return NULL;
    }
    unsigned char *out = (unsigned char*)PyBytes_AS_STRING(out_obj);

    Py_ssize_t out_idx = 0;
    for (Py_ssize_t q = 0; q < full_quanta; q++) {
        Py_ssize_t base = q * 8;
        int is_last = (q == full_quanta - 1 && padchars > 0);
        int valid_chars = is_last ? (int)(8 - padchars) : 8;

        uint64_t acc = 0;
        for (int k = 0; k < valid_chars; k++) {
            unsigned char c = in[base + k];
            int16_t d = rev[c];
            if (d < 0) {
                Py_DECREF(out_obj);
                PyErr_SetString(BinasciiError, "Non-base32 digit found");
                return NULL;
            }
            acc = (acc << 5) | (uint64_t)d;
        }

        if (is_last) {
            acc <<= (5 * padchars);
            int leftover = (int)(out_len - out_idx);
            for (int k = 0; k < leftover; k++) {
                out[out_idx++] = (unsigned char)((acc >> (32 - k * 8)) & 0xFF);
            }
        } else {
            out[out_idx++] = (unsigned char)((acc >> 32) & 0xFF);
            out[out_idx++] = (unsigned char)((acc >> 24) & 0xFF);
            out[out_idx++] = (unsigned char)((acc >> 16) & 0xFF);
            out[out_idx++] = (unsigned char)((acc >> 8) & 0xFF);
            out[out_idx++] = (unsigned char)(acc & 0xFF);
        }
    }
    return out_obj;
}

/* ========================================================================= */
/* Base32 / Base32Hex Python wrappers                                        */
/* ========================================================================= */
static PyObject* py_b32encode(PyObject* self, PyObject* args, PyObject* kwargs) {
    static char *kwlist[] = {"s", "alphabet", NULL};
    Py_buffer view;
    Py_buffer alpha_view = {NULL, NULL};
    const char *alphabet = B32_STD_ALPHABET;

    if (!PyArg_ParseTupleAndKeywords(args, kwargs, "y*|y*", kwlist, &view, &alpha_view)) {
        return NULL;
    }
    if (alpha_view.buf) {
        if (alpha_view.len != 32) {
            PyBuffer_Release(&view);
            PyBuffer_Release(&alpha_view);
            PyErr_SetString(PyExc_ValueError, "alphabet must be 32 bytes");
            return NULL;
        }
        alphabet = (const char*)alpha_view.buf;
    }

    PyObject *res = do_b32encode((const unsigned char*)view.buf, view.len, alphabet);
    PyBuffer_Release(&view);
    if (alpha_view.buf) PyBuffer_Release(&alpha_view);
    return res;
}

static PyObject* py_b32decode(PyObject* self, PyObject* args, PyObject* kwargs) {
    static char *kwlist[] = {"s", "alphabet", "casefold", "map01", NULL};
    Py_buffer view;
    Py_buffer alpha_view = {NULL, NULL};
    int casefold = 0;
    PyObject *map01_obj = NULL;
    const char *alphabet = B32_STD_ALPHABET;

    if (!PyArg_ParseTupleAndKeywords(args, kwargs, "y*|y*$pO", kwlist,
                                     &view, &alpha_view, &casefold, &map01_obj)) {
        return NULL;
    }
    if (alpha_view.buf) {
        if (alpha_view.len != 32) {
            PyBuffer_Release(&view);
            PyBuffer_Release(&alpha_view);
            PyErr_SetString(PyExc_ValueError, "alphabet must be 32 bytes");
            return NULL;
        }
        alphabet = (const char*)alpha_view.buf;
    }

    PyObject *res = do_b32decode((const unsigned char*)view.buf, view.len, alphabet, casefold, map01_obj);
    PyBuffer_Release(&view);
    if (alpha_view.buf) PyBuffer_Release(&alpha_view);
    return res;
}

static PyObject* py_b32hexencode(PyObject* self, PyObject* args) {
    Py_buffer view;
    if (!PyArg_ParseTuple(args, "y*", &view)) return NULL;
    PyObject *res = do_b32encode((const unsigned char*)view.buf, view.len, B32_HEX_ALPHABET);
    PyBuffer_Release(&view);
    return res;
}

static PyObject* py_b32hexdecode(PyObject* self, PyObject* args, PyObject* kwargs) {
    static char *kwlist[] = {"s", "casefold", NULL};
    Py_buffer view;
    int casefold = 0;
    if (!PyArg_ParseTupleAndKeywords(args, kwargs, "y*|$p", kwlist, &view, &casefold)) return NULL;
    PyObject *res = do_b32decode((const unsigned char*)view.buf, view.len, B32_HEX_ALPHABET, casefold, NULL);
    PyBuffer_Release(&view);
    return res;
}

/* ========================================================================= */
/* Base85 Encode / Decode                                                    */
/* ========================================================================= */
static PyObject* py_b85encode(PyObject* self, PyObject* args, PyObject* kwargs) {
    static char *kwlist[] = {"b", "pad", NULL};
    Py_buffer view;
    int pad = 0;

    if (!PyArg_ParseTupleAndKeywords(args, kwargs, "y*|$p", kwlist, &view, &pad)) {
        return NULL;
    }

    Py_ssize_t in_len = view.len;
    const unsigned char *in = (const unsigned char*)view.buf;

    if (in_len == 0) {
        PyBuffer_Release(&view);
        return PyBytes_FromStringAndSize("", 0);
    }

    int padding = (int)((-in_len) & 3);
    Py_ssize_t num_words = (in_len + padding) / 4;
    Py_ssize_t out_len = num_words * 5;
    if (!pad && padding) {
        out_len -= padding;
    }

    PyObject *out_obj = PyBytes_FromStringAndSize(NULL, out_len);
    if (!out_obj) {
        PyBuffer_Release(&view);
        return NULL;
    }
    char *out = PyBytes_AS_STRING(out_obj);

    Py_ssize_t i = 0, j = 0;
    while (i + 4 <= in_len) {
        uint32_t val = ((uint32_t)in[i] << 24) |
                       ((uint32_t)in[i+1] << 16) |
                       ((uint32_t)in[i+2] << 8) |
                       ((uint32_t)in[i+3]);
        out[j]   = B85_ALPHABET[val / 52200625U];
        out[j+1] = B85_ALPHABET[(val / 614125U) % 85U];
        out[j+2] = B85_ALPHABET[(val / 7225U) % 85U];
        out[j+3] = B85_ALPHABET[(val / 85U) % 85U];
        out[j+4] = B85_ALPHABET[val % 85U];
        i += 4;
        j += 5;
    }

    if (padding) {
        uint32_t val = 0;
        int leftover = (int)(in_len - i);
        for (int k = 0; k < leftover; k++) {
            val |= ((uint32_t)in[i + k]) << (24 - k * 8);
        }
        char chunk[5];
        chunk[0] = B85_ALPHABET[val / 52200625U];
        chunk[1] = B85_ALPHABET[(val / 614125U) % 85U];
        chunk[2] = B85_ALPHABET[(val / 7225U) % 85U];
        chunk[3] = B85_ALPHABET[(val / 85U) % 85U];
        chunk[4] = B85_ALPHABET[val % 85U];

        int to_copy = pad ? 5 : (5 - padding);
        for (int k = 0; k < to_copy; k++) {
            out[j + k] = chunk[k];
        }
    }

    PyBuffer_Release(&view);
    return out_obj;
}

static PyObject* py_b85decode(PyObject* self, PyObject* args) {
    Py_buffer view;
    if (!PyArg_ParseTuple(args, "y*", &view)) {
        return NULL;
    }

    Py_ssize_t in_len = view.len;
    const unsigned char *in = (const unsigned char*)view.buf;

    if (in_len == 0) {
        PyBuffer_Release(&view);
        return PyBytes_FromStringAndSize("", 0);
    }

    static int16_t b85_rev[256];
    static int rev_init = 0;
    if (!rev_init) {
        memset(b85_rev, -1, sizeof(b85_rev));
        for (int k = 0; k < 85; k++) {
            b85_rev[(unsigned char)B85_ALPHABET[k]] = (int16_t)k;
        }
        rev_init = 1;
    }

    int padding = (int)((-in_len) % 5);
    if (padding < 0) padding += 5;
    Py_ssize_t num_chunks = (in_len + padding) / 5;
    Py_ssize_t out_len = num_chunks * 4 - padding;

    PyObject *out_obj = PyBytes_FromStringAndSize(NULL, out_len);
    if (!out_obj) {
        PyBuffer_Release(&view);
        return NULL;
    }
    unsigned char *out = (unsigned char*)PyBytes_AS_STRING(out_obj);

    Py_ssize_t out_idx = 0;
    for (Py_ssize_t chunk_idx = 0; chunk_idx < num_chunks; chunk_idx++) {
        Py_ssize_t base = chunk_idx * 5;
        uint64_t acc = 0;
        for (int k = 0; k < 5; k++) {
            Py_ssize_t pos = base + k;
            unsigned char c = (pos < in_len) ? in[pos] : '~';
            int16_t d = b85_rev[c];
            if (d < 0) {
                Py_DECREF(out_obj);
                PyBuffer_Release(&view);
                PyErr_Format(PyExc_ValueError, "bad base85 character at position %zd", pos);
                return NULL;
            }
            acc = acc * 85U + (uint64_t)d;
        }

        if (acc > 0xFFFFFFFFU) {
            Py_DECREF(out_obj);
            PyBuffer_Release(&view);
            PyErr_Format(PyExc_ValueError, "base85 overflow in hunk starting at byte %zd", base);
            return NULL;
        }

        int write_bytes = (chunk_idx == num_chunks - 1 && padding > 0) ? (4 - padding) : 4;
        if (write_bytes >= 1) out[out_idx++] = (unsigned char)((acc >> 24) & 0xFF);
        if (write_bytes >= 2) out[out_idx++] = (unsigned char)((acc >> 16) & 0xFF);
        if (write_bytes >= 3) out[out_idx++] = (unsigned char)((acc >> 8) & 0xFF);
        if (write_bytes >= 4) out[out_idx++] = (unsigned char)(acc & 0xFF);
    }

    PyBuffer_Release(&view);
    return out_obj;
}

/* ========================================================================= */
/* ZeroMQ (Z85) Encode / Decode                                              */
/* ========================================================================= */
static PyObject* py_z85encode(PyObject* self, PyObject* args) {
    Py_buffer view;
    if (!PyArg_ParseTuple(args, "y*", &view)) {
        return NULL;
    }

    Py_ssize_t in_len = view.len;
    if (in_len % 4 != 0) {
        PyBuffer_Release(&view);
        PyErr_SetString(PyExc_ValueError, "Z85 length must be multiple of 4 bytes");
        return NULL;
    }

    if (in_len == 0) {
        PyBuffer_Release(&view);
        return PyBytes_FromStringAndSize("", 0);
    }

    const unsigned char *in = (const unsigned char*)view.buf;
    Py_ssize_t out_len = (in_len / 4) * 5;
    PyObject *out_obj = PyBytes_FromStringAndSize(NULL, out_len);
    if (!out_obj) {
        PyBuffer_Release(&view);
        return NULL;
    }
    char *out = PyBytes_AS_STRING(out_obj);

    Py_ssize_t i = 0, j = 0;
    while (i < in_len) {
        uint32_t val = ((uint32_t)in[i] << 24) |
                       ((uint32_t)in[i+1] << 16) |
                       ((uint32_t)in[i+2] << 8) |
                       ((uint32_t)in[i+3]);
        out[j]   = Z85_ALPHABET[val / 52200625U];
        out[j+1] = Z85_ALPHABET[(val / 614125U) % 85U];
        out[j+2] = Z85_ALPHABET[(val / 7225U) % 85U];
        out[j+3] = Z85_ALPHABET[(val / 85U) % 85U];
        out[j+4] = Z85_ALPHABET[val % 85U];
        i += 4;
        j += 5;
    }

    PyBuffer_Release(&view);
    return out_obj;
}

static PyObject* py_z85decode(PyObject* self, PyObject* args) {
    Py_buffer view;
    if (!PyArg_ParseTuple(args, "y*", &view)) {
        return NULL;
    }

    Py_ssize_t in_len = view.len;
    if (in_len % 5 != 0) {
        PyBuffer_Release(&view);
        PyErr_SetString(PyExc_ValueError, "Z85 length must be multiple of 5 characters");
        return NULL;
    }

    if (in_len == 0) {
        PyBuffer_Release(&view);
        return PyBytes_FromStringAndSize("", 0);
    }

    static int16_t z85_rev[256];
    static int rev_init = 0;
    if (!rev_init) {
        memset(z85_rev, -1, sizeof(z85_rev));
        for (int k = 0; k < 85; k++) {
            z85_rev[(unsigned char)Z85_ALPHABET[k]] = (int16_t)k;
        }
        rev_init = 1;
    }

    const unsigned char *in = (const unsigned char*)view.buf;
    Py_ssize_t out_len = (in_len / 5) * 4;
    PyObject *out_obj = PyBytes_FromStringAndSize(NULL, out_len);
    if (!out_obj) {
        PyBuffer_Release(&view);
        return NULL;
    }
    unsigned char *out = (unsigned char*)PyBytes_AS_STRING(out_obj);

    Py_ssize_t i = 0, j = 0;
    while (i < in_len) {
        uint64_t acc = 0;
        for (int k = 0; k < 5; k++) {
            unsigned char c = in[i + k];
            int16_t d = z85_rev[c];
            if (d < 0) {
                Py_DECREF(out_obj);
                PyBuffer_Release(&view);
                PyErr_Format(PyExc_ValueError, "bad z85 character at position %zd", i + k);
                return NULL;
            }
            acc = acc * 85U + (uint64_t)d;
        }
        if (acc > 0xFFFFFFFFU) {
            Py_DECREF(out_obj);
            PyBuffer_Release(&view);
            PyErr_Format(PyExc_ValueError, "z85 overflow in hunk starting at byte %zd", i);
            return NULL;
        }
        out[j]   = (unsigned char)((acc >> 24) & 0xFF);
        out[j+1] = (unsigned char)((acc >> 16) & 0xFF);
        out[j+2] = (unsigned char)((acc >> 8) & 0xFF);
        out[j+3] = (unsigned char)(acc & 0xFF);
        i += 5;
        j += 4;
    }

    PyBuffer_Release(&view);
    return out_obj;
}

/* ========================================================================= */
/* Ascii85 Encode / Decode                                                   */
/* ========================================================================= */
static PyObject* py_a85encode(PyObject* self, PyObject* args, PyObject* kwargs) {
    static char *kwlist[] = {"b", "foldspaces", "wrapcol", "pad", "adobe", NULL};
    Py_buffer view;
    int foldspaces = 0;
    int wrapcol = 0;
    int pad = 0;
    int adobe = 0;

    if (!PyArg_ParseTupleAndKeywords(args, kwargs, "y*|$pipp", kwlist,
                                     &view, &foldspaces, &wrapcol, &pad, &adobe)) {
        return NULL;
    }

    Py_ssize_t in_len = view.len;
    const unsigned char *in = (const unsigned char*)view.buf;

    int padding = (int)((-in_len) & 3);
    Py_ssize_t num_words = (in_len + padding) / 4;

    Py_ssize_t est_len = num_words * 5 + 4 + (wrapcol > 0 ? (num_words * 5 / wrapcol + 2) : 0) + 16;
    char *buf = (char*)PyMem_Malloc(est_len);
    if (!buf) {
        PyBuffer_Release(&view);
        return PyErr_NoMemory();
    }

    Py_ssize_t out_idx = 0;
    Py_ssize_t col = 0;

    if (adobe) {
        buf[out_idx++] = '<';
        buf[out_idx++] = '~';
        col += 2;
    }

    #define EMIT_CHAR(ch) do { \
        if (wrapcol > 0 && col >= wrapcol) { \
            buf[out_idx++] = '\n'; \
            col = 0; \
        } \
        buf[out_idx++] = (ch); \
        col++; \
    } while (0)

    Py_ssize_t i = 0;
    while (i + 4 <= in_len) {
        uint32_t val = ((uint32_t)in[i] << 24) |
                       ((uint32_t)in[i+1] << 16) |
                       ((uint32_t)in[i+2] << 8) |
                       ((uint32_t)in[i+3]);
        if (foldspaces && val == 0x20202020U) {
            EMIT_CHAR('y');
        } else {
            EMIT_CHAR((char)((val / 52200625U) + 33));
            EMIT_CHAR((char)(((val / 614125U) % 85U) + 33));
            EMIT_CHAR((char)(((val / 7225U) % 85U) + 33));
            EMIT_CHAR((char)(((val / 85U) % 85U) + 33));
            EMIT_CHAR((char)((val % 85U) + 33));
        }
        i += 4;
    }

    if (padding) {
        uint32_t val = 0;
        int leftover = (int)(in_len - i);
        for (int k = 0; k < leftover; k++) {
            val |= ((uint32_t)in[i + k]) << (24 - k * 8);
        }
        char chunk[5];
        chunk[0] = (char)((val / 52200625U) + 33);
        chunk[1] = (char)(((val / 614125U) % 85U) + 33);
        chunk[2] = (char)(((val / 7225U) % 85U) + 33);
        chunk[3] = (char)(((val / 85U) % 85U) + 33);
        chunk[4] = (char)((val % 85U) + 33);

        int to_emit = pad ? 5 : (5 - padding);
        for (int k = 0; k < to_emit; k++) {
            EMIT_CHAR(chunk[k]);
        }
    }

    if (adobe) {
        if (wrapcol > 0 && col + 2 > wrapcol) {
            buf[out_idx++] = '\n';
        }
        buf[out_idx++] = '~';
        buf[out_idx++] = '>';
    }

    #undef EMIT_CHAR

    PyObject *res = PyBytes_FromStringAndSize(buf, out_idx);
    PyMem_Free(buf);
    PyBuffer_Release(&view);
    return res;
}

static PyObject* py_a85decode(PyObject* self, PyObject* args, PyObject* kwargs) {
    static char *kwlist[] = {"b", "foldspaces", "adobe", "ignorechars", NULL};
    Py_buffer view;
    int foldspaces = 0;
    int adobe = 0;
    Py_buffer ignore_view = {NULL, NULL};

    if (!PyArg_ParseTupleAndKeywords(args, kwargs, "y*|$ppy*", kwlist,
                                     &view, &foldspaces, &adobe, &ignore_view)) {
        return NULL;
    }

    const unsigned char *in = (const unsigned char*)view.buf;
    Py_ssize_t in_len = view.len;

    uint8_t ignore_table[256];
    memset(ignore_table, 0, sizeof(ignore_table));
    if (ignore_view.buf) {
        const unsigned char *ig = (const unsigned char*)ignore_view.buf;
        for (Py_ssize_t k = 0; k < ignore_view.len; k++) {
            ignore_table[ig[k]] = 1;
        }
    } else {
        ignore_table[(unsigned char)' '] = 1;
        ignore_table[(unsigned char)'\t'] = 1;
        ignore_table[(unsigned char)'\n'] = 1;
        ignore_table[(unsigned char)'\r'] = 1;
        ignore_table[(unsigned char)'\v'] = 1;
    }

    Py_ssize_t start = 0;
    Py_ssize_t end = in_len;

    if (adobe) {
        while (start < end && ignore_table[in[start]]) start++;
        if (start + 2 <= end && in[start] == '<' && in[start + 1] == '~') {
            start += 2;
        }
        while (end > start && ignore_table[in[end - 1]]) end--;
        if (end - start >= 2 && in[end - 2] == '~' && in[end - 1] == '>') {
            end -= 2;
        }
    }

    Py_ssize_t max_out = (end - start) * 4 + 16;
    unsigned char *out = (unsigned char*)PyMem_Malloc(max_out > 1 ? max_out : 1);
    if (!out) {
        PyBuffer_Release(&view);
        if (ignore_view.buf) PyBuffer_Release(&ignore_view);
        return PyErr_NoMemory();
    }

    Py_ssize_t out_idx = 0;
    uint32_t chunk[5];
    int chunk_len = 0;

    for (Py_ssize_t i = start; i < end; i++) {
        unsigned char c = in[i];
        if (ignore_table[c]) continue;

        if (c == 'z' && chunk_len == 0) {
            out[out_idx++] = 0;
            out[out_idx++] = 0;
            out[out_idx++] = 0;
            out[out_idx++] = 0;
            continue;
        }
        if (foldspaces && c == 'y' && chunk_len == 0) {
            out[out_idx++] = 0x20;
            out[out_idx++] = 0x20;
            out[out_idx++] = 0x20;
            out[out_idx++] = 0x20;
            continue;
        }

        if (c < '!' || c > 'u') {
            PyMem_Free(out);
            PyBuffer_Release(&view);
            if (ignore_view.buf) PyBuffer_Release(&ignore_view);
            PyErr_Format(PyExc_ValueError, "bad ascii85 character at byte %zd", i);
            return NULL;
        }

        chunk[chunk_len++] = (uint32_t)(c - 33);
        if (chunk_len == 5) {
            uint64_t acc = (uint64_t)chunk[0] * 52200625ULL +
                           (uint64_t)chunk[1] * 614125ULL +
                           (uint64_t)chunk[2] * 7225ULL +
                           (uint64_t)chunk[3] * 85ULL +
                           (uint64_t)chunk[4];
            if (acc > 0xFFFFFFFFU) {
                PyMem_Free(out);
                PyBuffer_Release(&view);
                if (ignore_view.buf) PyBuffer_Release(&ignore_view);
                PyErr_Format(PyExc_ValueError, "ascii85 overflow in hunk starting at byte %zd", i - 4);
                return NULL;
            }
            out[out_idx++] = (unsigned char)((acc >> 24) & 0xFF);
            out[out_idx++] = (unsigned char)((acc >> 16) & 0xFF);
            out[out_idx++] = (unsigned char)((acc >> 8) & 0xFF);
            out[out_idx++] = (unsigned char)(acc & 0xFF);
            chunk_len = 0;
        }
    }

    if (chunk_len > 0) {
        if (chunk_len == 1) {
            PyMem_Free(out);
            PyBuffer_Release(&view);
            if (ignore_view.buf) PyBuffer_Release(&ignore_view);
            PyErr_SetString(PyExc_ValueError, "bad ascii85 trailing quantum");
            return NULL;
        }
        for (int k = chunk_len; k < 5; k++) {
            chunk[k] = 84;
        }
        uint64_t acc = (uint64_t)chunk[0] * 52200625ULL +
                       (uint64_t)chunk[1] * 614125ULL +
                       (uint64_t)chunk[2] * 7225ULL +
                       (uint64_t)chunk[3] * 85ULL +
                       (uint64_t)chunk[4];
        if (acc > 0xFFFFFFFFU) {
            PyMem_Free(out);
            PyBuffer_Release(&view);
            if (ignore_view.buf) PyBuffer_Release(&ignore_view);
            PyErr_SetString(PyExc_ValueError, "ascii85 overflow in trailing hunk");
            return NULL;
        }
        int write_bytes = chunk_len - 1;
        if (write_bytes >= 1) out[out_idx++] = (unsigned char)((acc >> 24) & 0xFF);
        if (write_bytes >= 2) out[out_idx++] = (unsigned char)((acc >> 16) & 0xFF);
        if (write_bytes >= 3) out[out_idx++] = (unsigned char)((acc >> 8) & 0xFF);
    }

    PyObject *res = PyBytes_FromStringAndSize((char*)out, out_idx);
    PyMem_Free(out);
    PyBuffer_Release(&view);
    if (ignore_view.buf) PyBuffer_Release(&ignore_view);
    return res;
}

/* ========================================================================= */
/* Module Definition                                                         */
/* ========================================================================= */
static PyMethodDef SpeedupMethods[] = {
    {"b32encode", (PyCFunction)py_b32encode, METH_VARARGS | METH_KEYWORDS, "Fast Base32 encode"},
    {"b32decode", (PyCFunction)py_b32decode, METH_VARARGS | METH_KEYWORDS, "Fast Base32 decode"},
    {"b32hexencode", (PyCFunction)py_b32hexencode, METH_VARARGS, "Fast Base32Hex encode"},
    {"b32hexdecode", (PyCFunction)py_b32hexdecode, METH_VARARGS | METH_KEYWORDS, "Fast Base32Hex decode"},
    {"b85encode", (PyCFunction)py_b85encode, METH_VARARGS | METH_KEYWORDS, "Fast Base85 encode"},
    {"b85decode", (PyCFunction)py_b85decode, METH_VARARGS, "Fast Base85 decode"},
    {"z85encode", (PyCFunction)py_z85encode, METH_VARARGS, "Fast Z85 encode"},
    {"z85decode", (PyCFunction)py_z85decode, METH_VARARGS, "Fast Z85 decode"},
    {"a85encode", (PyCFunction)py_a85encode, METH_VARARGS | METH_KEYWORDS, "Fast Ascii85 encode"},
    {"a85decode", (PyCFunction)py_a85decode, METH_VARARGS | METH_KEYWORDS, "Fast Ascii85 decode"},
    {NULL, NULL, 0, NULL}
};

static struct PyModuleDef speedups_module = {
    PyModuleDef_HEAD_INIT,
    "_speedups",
    "C accelerated implementations of Base32, Base85, Z85, and Ascii85",
    -1,
    SpeedupMethods
};

PyMODINIT_FUNC PyInit__speedups(void) {
    PyObject *binascii_mod = PyImport_ImportModule("binascii");
    if (binascii_mod) {
        BinasciiError = PyObject_GetAttrString(binascii_mod, "Error");
        Py_DECREF(binascii_mod);
    }
    if (!BinasciiError) {
        BinasciiError = PyExc_ValueError;
    }
    return PyModule_Create(&speedups_module);
}
