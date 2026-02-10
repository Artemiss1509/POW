import ssl
import socket
import string, random
import hashlib
import multiprocessing
import os


context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)

context.check_hostname = False
context.verify_mode = ssl.CERT_NONE
context.load_cert_chain(certfile="challenge-38-c-.pem", keyfile="challenge-38-c-.pem")

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
tls_sock = context.wrap_socket(sock, server_hostname="18.202.148.130")

tls_sock.settimeout(10)
tls_sock.connect(("18.202.148.130", 3336))

conn = tls_sock.makefile('rwb')
authdata = ''

def pow_worker(authdata, difficulty):
    chars = string.ascii_letters + string.digits
    prefix = "0" * difficulty

    while True:
        suffix = ''.join(random.choices(chars, k=16))
        digest = hashlib.sha1((authdata + suffix).encode("utf-8")).hexdigest()
        if digest.startswith(prefix):
            return suffix

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

            if args[0] == "HELO":
                print("→ Sending EHLO")
                conn.write(b"EHLO\n")
                conn.flush()

            elif args[0] == "ERROR":
                print("ERROR:", " ".join(args[1:]))
                break

            elif args[0] == "POW":

                tls_sock.settimeout(None)
                authdata,  difficulty = args[1], int(args[2])

                cpu_count = os.cpu_count()
                print("→ Using", cpu_count, "processes")

                pool = multiprocessing.Pool(processes=cpu_count)
                results = []

                for _ in range(cpu_count):
                    results.append(pool.apply_async(pow_worker(authdata, difficulty)))

                found_suffix = None
                for result in results:
                    suffix = result.get()
                    if suffix:
                        found_suffix = suffix
                        break

                pool.terminate()
                pool.join()

                conn.write((found_suffix + "\n").encode("utf-8"))
                conn.flush()
                tls_sock.settimeout(10)
            
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