/* Process-scoped connection fault injection for native qualification.
 * Allow local GUI/DBus/MCP IPC; refuse external TCP and the network-backed
 * snapd socket. This is a test fixture, not a network sandbox/security boundary.
 */
#define _GNU_SOURCE
#include <dlfcn.h>
#include <errno.h>
#include <netinet/in.h>
#include <stddef.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/un.h>

int connect(int fd, const struct sockaddr *address, socklen_t length) {
    if (address && address->sa_family == AF_INET && length >= sizeof(struct sockaddr_in)) {
        const struct sockaddr_in *value = (const struct sockaddr_in *)address;
        if ((ntohl(value->sin_addr.s_addr) >> 24) != 127) {
            errno = ENETUNREACH;
            return -1;
        }
    }
    if (address && address->sa_family == AF_INET6 && length >= sizeof(struct sockaddr_in6)) {
        const struct sockaddr_in6 *value = (const struct sockaddr_in6 *)address;
        if (!IN6_IS_ADDR_LOOPBACK(&value->sin6_addr)) {
            errno = ENETUNREACH;
            return -1;
        }
    }
    if (address && address->sa_family == AF_UNIX && length >= offsetof(struct sockaddr_un, sun_path) + sizeof("/run/snapd.socket")) {
        const struct sockaddr_un *value = (const struct sockaddr_un *)address;
        if (memcmp(value->sun_path, "/run/snapd.socket", sizeof("/run/snapd.socket")) == 0) {
            errno = ENETUNREACH;
            return -1;
        }
    }
    int (*native_connect)(int, const struct sockaddr *, socklen_t) = dlsym(RTLD_NEXT, "connect");
    if (!native_connect) { errno = ENOSYS; return -1; }
    return native_connect(fd, address, length);
}
