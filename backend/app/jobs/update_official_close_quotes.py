from pprint import pprint
from ..services.official_close_quotes import update_official_close_quotes


def main():
    pprint(update_official_close_quotes())


if __name__ == "__main__":
    main()
