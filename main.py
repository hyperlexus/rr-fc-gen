from generate_fcs import generate_fcs

if __name__ == "__main__":
    total_pids_to_use = 1_000_000_000  # max is 1 billion. takes 3 hours!!
    generate_fcs(total_pids_to_use)
