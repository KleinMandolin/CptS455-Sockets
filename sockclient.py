from pathlib import Path
import socket
import struct
from tqdm import tqdm

# file receive/send code (defining file size, sending in 1024 sized chunks) adapted from: 
#   https://pythonassets.com/posts/send-file-via-socket/
# progress bar code adapted from: 
#   https://idiotdeveloper.com/large-file-transfer-using-tcp-socket-in-python/
# both were for a specific predefined file transfer, code was adapted for dynamic file sending

# send out file, assuming valid file
def send_file(path: Path, out_message: str):
    filename=path.name
    filesize=path.stat().st_size
    print("Sending "+ str(filename) + " [size: " + str(filesize) + " bytes]")
    # warn server to ready for file
    conn.send((str(out_message) + '\0' + filename).encode())
    # wait for server ready
    in_message = conn.recv(1024).decode()
    print("Server " + in_message +" for file.")
    # send file in chunks
    conn.sendall(struct.pack("<Q", filesize))
    with open(path, "rb") as file:
        while read_bytes := file.read(1024):
            conn.sendall(read_bytes)
    print("Sent.")
    
def receive_file(in_message: str):
    filename = (in_message.split('\0'))[1]
    print("Client sending file: "+ filename)
    # prep for file incoming
    fmt = "<Q"
    expected_bytes = struct.calcsize(fmt)
    received_bytes = 0
    stream = bytes()
    # tell client ready for file
    conn.send(("ready").encode())
    # have client send total size of file with checksum
    while received_bytes < expected_bytes:
        chunk = conn.recv(expected_bytes - received_bytes)
        stream += chunk
        received_bytes +=len(chunk)
    filesize = struct.unpack(fmt, stream) [0]
    # progress bar for receiving/downloading file
    bar = tqdm(range(filesize), f"Receiving {filename}", unit="B", unit_scale=True, unit_divisor=1024, miniters=1)
    # begin receiving file in 1024 byte chunks
    with open(filename, "wb") as file:
        received_bytes = 0
        while received_bytes < filesize:
            chunk = conn.recv(1024)
            if chunk:
                file.write(chunk)
                received_bytes += len(chunk)
                bar.update(len(chunk))


with socket.create_connection(("localhost", 4456)) as conn:
    print("Connected to server.\n")
    print("Commands:")
    print("     /exit -> leave and close connection")
    print("     /send [filepath] -> send given file to server")
    out_message = input("-> ")
    # used in case user incorrectly entered /send command
    message_sent=False
    while out_message != "/exit":
        
        ##
        # process client out_message
        ##
        
        # /send command
        if out_message.startswith("/send"):
            sections = out_message.split(' ',1)
            if len(sections) == 2:
                input_path=sections[1]
                path=Path(input_path.replace('"', ''))
                if not path.exists():
                    print("Could not find " + input_path + "! File Sending Command: /send [filepath]")
                elif not path.is_file():
                    print("Not a file! File Sending Command: /send [filepath]")
                
                # begin sending
                # sending socket code from: https://pythonassets.com/posts/send-file-via-socket/
                else:
                    send_file(path, out_message)
                    message_sent=True
            else:
                print("No filepath included! File Sending Command: /send [filepath]")
        # client sending chat message
        else:
            conn.send(out_message.encode())
            message_sent=True
        
        ##
        # process server in_message
        ##
        if message_sent:
            in_message = conn.recv(1024).decode()
            # server sending file
            if str(in_message).startswith("/send"):
                receive_file(in_message)
                print("File successfully received.")
            # server sent chat message
            else:
                print('Received from server: ' + in_message)  # show in terminal

        # end of loop, get next input
        out_message = input("-> ")
        message_sent=False
    print("Goodbye!")