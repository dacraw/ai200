"""Two races that a threading.Lock prevents, stripped down to run standalone.

Run it:  python thread_demo.py
"""

import sys
import threading
import time
from collections import deque


class MessageBuffer:
    """A tiny stand-in for PubSubManager's message buffer.

    Pass use_lock=False to disable protection and watch it break.
    """

    def __init__(self, use_lock=True):
        self._messages = deque(maxlen=500)
        self._counter = 0
        self._lock = threading.Lock() if use_lock else _NoLock()

    def add(self, text):
        with self._lock:
            self._counter += 1
            self._messages.append({"index": self._counter, "text": text})

    def get_since(self, since):
        with self._lock:
            # Iterating while another thread appends is the dangerous part.
            return [m for m in self._messages if m["index"] > since]


class _NoLock:
    """Does nothing. Lets the same code run locked or unlocked."""

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def demo_mutation_during_iteration(use_lock):
    """A reader iterating the deque while a producer appends to it."""
    buf = MessageBuffer(use_lock=use_lock)
    errors = []
    stop = threading.Event()

    def producer():
        while not stop.is_set():
            buf.add("published")

    def reader():
        while not stop.is_set():
            try:
                buf.get_since(0)
            except RuntimeError as e:
                errors.append(str(e))
                return

    threads = [threading.Thread(target=producer), threading.Thread(target=reader)]
    for t in threads:
        t.start()
    time.sleep(10.0)
    stop.set()
    for t in threads:
        t.join()

    label = "WITH lock" if use_lock else "WITHOUT lock"
    if errors:
        print(f"  {label}:  crashed -> RuntimeError: {errors[0]}")
    else:
        print(f"  {label}:  survived 1s of concurrent reads and writes")


def demo_clear_desync(use_lock):
    """A reader observing clear_messages() halfway through.

    clear_messages does two things: empties the deque, then resets the
    counter. Between those two statements the object is in a state that
    should never be visible. The sleep does not create the window - it
    just widens one that is already there.
    """
    buf = MessageBuffer(use_lock=use_lock)
    for i in range(5):
        buf.add(f"message {i}")

    observed = []

    def clearer():
        with buf._lock:
            buf._messages.clear()
            time.sleep(0.05)
            buf._counter = 0

    def reader():
        time.sleep(0.02)
        with buf._lock:
            observed.append((len(buf._messages), buf._counter))

    threads = [threading.Thread(target=clearer), threading.Thread(target=reader)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    size, counter = observed[0]
    label = "WITH lock" if use_lock else "WITHOUT lock"
    verdict = "torn state" if (size == 0 and counter != 0) else "consistent"
    print(f"  {label}:  reader saw {size} messages, counter={counter}  -> {verdict}")


if __name__ == "__main__":
    print("\n1. Reader iterating the deque while the producer appends")
    demo_mutation_during_iteration(use_lock=False)
    demo_mutation_during_iteration(use_lock=True)

    print("\n2. Reader landing inside clear_messages")
    demo_clear_desync(use_lock=False)
    demo_clear_desync(use_lock=True)
    print()