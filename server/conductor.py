import hakopy

def main(delta_time_usec, max_delay_time_usec):
    while True:
        hakopy.conductor_start(delta_time_usec, max_delay_time_usec)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Hakoniwa Conductor")
    parser.add_argument('--delta_time_usec', type=int, required=True, help='Delta time in microseconds')
    parser.add_argument('--max_delay_time_usec', type=int, required=True, help='Max delay time in microseconds')
    args = parser.parse_args()

    main(args.delta_time_usec, args.max_delay_time_usec)