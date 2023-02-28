# leakyBuckets

Look for open storage buckets and accessible files simultaneously across Amazon Web Services, Google Cloud, and Microsoft Azure

## Install

    git clone https://github.com/chm0dx/leakyBuckets.git
    cd leakyBuckets
    pip install -r requirements.txt

## Use

    leakyBuckets.py [--keywords KEYWORDS] [--modifiers MODIFIERS] [--guesses GUESSES]
                    [--az-storage-accounts AZ_STORAGE_ACCOUNTS] [--threads THREADS]
                    [--max-files MAX_FILES] [--max-size MAX_SIZE] [--download]

    Find open storage buckets and accessible files across Amazon Web Services, Google Cloud, and Microsoft Azure simultaneously

    optional arguments:
      -h, --help            show this help message and exit
      --keywords KEYWORDS   Keywords used to generate guesses. Can be a path to a wordlist file or comma-separated list of words.
      --modifiers MODIFIERS
                            Used to modify keywords. Can be a path to a wordlist file or comma-separated list of words.
      --guesses GUESSES     Manually provide guesses. Can be a path to a wordlist file or comma-separated list of words.
      --az-storage-accounts AZ_STORAGE_ACCOUNTS
                            Provide Azure storage accounts (defaults to either keywords or guesses, whichever is passed in). Can be a path to a wordlist file or comma-separated list of words.
      --threads THREADS     The max number of threads to use. Defaults to 10.
      --max-files MAX_FILES
                            The max number of items to list/download from each bucket. Defaults to 100.
      --max-size MAX_SIZE   The max file size (in bytes) to download.
      --download            Attempt to download discovered files.


![...](https://media0.giphy.com/media/VeSvZhPrqgZxx2KpOA/giphy.gif)