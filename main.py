import ssl
import socket
import hashlib
import multiprocessing as mp
import os


context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)

context.check_hostname = False
context.verify_mode = ssl.CERT_NONE
context.load_cert_chain(certfile="challenge-38-c-.pem", keyfile="challenge-38-c-.pem")

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
tls_sock = context.wrap_socket(sock, server_hostname="18.202.148.130")

tls_sock.settimeout(6)
tls_sock.connect(("18.202.148.130", 3336))

conn = tls_sock.makefile('rwb')
authdata = ''
STOP_EVENT = None
def _init_worker(stop_event):
    global STOP_EVENT
    STOP_EVENT = stop_event


def pow_worker_optimized(authdata: str, difficulty: int, start: int, step: int) -> str:
    auth_bytes = authdata.encode("utf-8")
    counter = start
    sha1 = hashlib.sha1
    event_is_set = STOP_EVENT.is_set
    event_set = STOP_EVENT.set

    full_bytes = difficulty // 2
    half_nibble = difficulty % 2
    zero_prefix = b"\x00" * full_bytes
    check_interval = 4096

    while True:
        for _ in range(check_interval):
            
            suffix = format(counter, "x").encode("ascii")
            h = sha1(auth_bytes + suffix).digest()
            counter += step

            if h[:full_bytes] == zero_prefix and (not half_nibble or (h[full_bytes] >> 4) == 0):
                event_set()
                return suffix.decode("ascii")

        if event_is_set():
            return None

    return None

def _worker_wrapper(args):
    return pow_worker_optimized(*args)


def solve_pow(authdata: str, difficulty: int) -> str:
    cpu_count = os.cpu_count() or 4
    print("-> Using", cpu_count, "processes")

    methods = mp.get_all_start_methods()
    method = "fork" if "fork" in methods else "spawn"
    ctx = mp.get_context(method)
    manager = None
    if method == "fork":
        stop_event = ctx.Event()
    else:
        manager = ctx.Manager()
        stop_event = manager.Event()

    tasks = [
        (authdata, difficulty, i, cpu_count)
        for i in range(cpu_count)
    ]

    with ctx.Pool(cpu_count, initializer=_init_worker, initargs=(stop_event,)) as pool:
        try:
            for result in pool.imap_unordered(_worker_wrapper, tasks):
                if result:
                    stop_event.set()
                    pool.terminate()
                    pool.join()
                    return result
        finally:
            pool.terminate()
            pool.join()
            if manager is not None:
                manager.shutdown()

    raise RuntimeError("PoW not solved")


def reply(token, value):
    digest = hashlib.sha1((authdata + token).encode("utf-8")).hexdigest()
    conn.write((digest + " " + value + "\n").encode("utf-8"))
    conn.flush()

def main():
    global authdata
    while True:
        try:
            line = conn.readline()
            if not line:
                print("Server closed the connection.")
                break

            line = line.decode("utf-8").strip()
            print("Received:", line)

            args = line.split()
            if not args:
                continue

            if args[0] == "HELO":
                print("-> Sending EHLO")
                conn.write(b"EHLO\n")
                conn.flush()

            elif args[0] == "ERROR":
                print("ERROR:", " ".join(args[1:]))
                break

            elif args[0] == "POW":
                tls_sock.settimeout(None)
                authdata, difficulty = args[1], int(args[2])

                found_suffix = solve_pow(authdata, difficulty)
                
                if not found_suffix:
                    print("ERROR: POW not solved")
                    break

                conn.write((found_suffix + "\n").encode("utf-8"))
                conn.flush()
                tls_sock.settimeout(6)
            
            elif args[0] == "END":
                conn.write(b"OK\n")
                conn.flush()
                break

            elif args[0] == "NAME":
                reply(args[1], "Rohan Sunil")
            
            elif args[0] == "MAILNUM":
                reply(args[1], "2")

            elif args[0] == "MAIL1":
                reply(args[1], "rohansunil32@gmail.com")

            elif args[0] == "MAIL2":
                reply(args[1], "rohansunil.s@gmail.com")

            elif args[0] == "SKYPE":
                reply(args[1], "N/A")

            elif args[0] == "BIRTHDATE":
                reply(args[1], "15.01.2000")

            elif args[0] == "COUNTRY":
                reply(args[1], "India")

            elif args[0] == "ADDRNUM":
                reply(args[1], "2")

            elif args[0] == "ADDRLINE1":
                reply(args[1], "17 Srirampet Street, CIT Nagar")

            elif args[0] == "ADDRLINE2":
                reply(args[1], "Chennai, Tamil Nadu 600035")



        except socket.timeout:
            print("Connection timed out.")
            break
        except Exception as e:
            print("An error occurred:", str(e))
            break
    conn.close()
    tls_sock.close()
    
if __name__ == "__main__":
    main()