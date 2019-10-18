"""
(A) use directly by passing a password as the first argument:

    $ python gen_pass.py mysecretpass

(B) use via a password protected entry,
    by not passing any argument.
"""

import sys
import getpass
import hashlib



def make_pass(pwd):
    import mmupload
    return hashlib.sha256(
        pwd.encode("utf-8") + b"//SALT//" +
        mmupload.app.secret_key.encode("utf-8")).hexdigest()

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <mmupload-config-path>")
        sys.exit(1)

    pwd = getpass.getpass("Password: ")
    pwd2 = getpass.getpass("Password (repeat): ")
    if pwd != pwd2:
        print("passwords don't match, exit...")
        sys.exit(1)

    print(make_pass(pwd))

