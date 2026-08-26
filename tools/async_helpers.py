import threading


def run_async(widget, work_fn, on_done):
    """
    work_fn выполняется в фоновом потоке (сеть/Supabase),
    on_done вызывается в главном потоке Tkinter с результатом,
    когда work_fn реально закончит работу — без таймеров.
    """
    def worker():
        try:
            result = work_fn()
        except Exception as exc:
            result = exc
        widget.after(0, lambda: on_done(result))

    threading.Thread(target=worker, daemon=True).start()