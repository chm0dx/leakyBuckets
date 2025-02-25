# leakyBuckets

Find open storage buckets and accessible files across Amazon Web Services, Google Cloud, Microsoft Azure, and Digital Ocean simultaneously

* One tool instead of four!
* Auto-generate guesses from one or more passed-in keywords
* Auto-download accessible files (with guard rails to protect disk space)
* Customizable threading
* Terrible name

![alt text](./demo.gif "Quick Demo")

## Install

    git clone https://github.com/chm0dx/leakyBuckets.git
    cd leakyBuckets
    pip install -r requirements.txt

## Use

    optional arguments:
    -h, --help            show this help message and exit
    --keywords KEYWORDS   Keywords used to generate guesses. File path or comma-separated list.
    --download            Automatically download discovered files.
    --guesses GUESSES     Manually provide guesses (instead of relying on the tool). File path or comma-separated list.
    --threads THREADS     The max number of threads to use. Defaults to 10.
    --max-files MAX_FILES
                            The max number of items to list/download from each bucket. Defaults to 100.
    --max-size MAX_SIZE   The max file size (in bytes) to download. Defaults to 100000000.
    --modifiers MODIFIERS
                            Used to modify keywords. File path or comma-separated list.
    --direct-download DIRECT_DOWNLOAD
                            Provide URLs of files to download. File path or comma-separated list.
    --az-accounts AZ_ACCOUNTS
                            Provide AZ storage accounts (defaults to passed-in keywords). File path or comma-separated list.
    --all                 Show all results, even if the bucket isn't open.

    Examples:
    python3 leakyBuckets.py --keywords hooli
    python3 leakyBuckets.py --keywords /path/to/keywords.txt --download --max-files 100 --max-size 10000
    python3 leakyBuckets.py --guesses hooli-dev,hoolibucket,hoolicon_files
    python3 leakyBuckets.py --keywords hooli --modifiers files,buckets,dev,staging,code
    python3 leakyBuckets.py --direct-download https://hooli.blob.core.windows.net/container/hooli3.gif
    python3 leakyBuckets.py --keywords hooli --modifiers /path/to/modifiers.txt --az-accounts hoolistorage,hooli_storage
&nbsp;

![...](https://media0.giphy.com/media/VeSvZhPrqgZxx2KpOA/giphy.gif)
