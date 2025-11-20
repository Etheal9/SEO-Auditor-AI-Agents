import sys
import traceback

try:
    print("Attempting to import main...")
    import main
    print("Main imported. Running main...")
    main.target_url = "https://www.example.com"
    main.main(main.target_url)
    print("Main finished.")
except Exception:
    print("Exception occurred!")
    with open("error.log", "w") as f:
        traceback.print_exc(file=f)
