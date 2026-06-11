from pprint import pprint

from ..services.realtime_quotes import update_live_quotes

def main():
    result = update_live_quotes()
    pprint(result)

if __name__ == "__main__":
    main()
