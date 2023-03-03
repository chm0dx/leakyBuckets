import itertools
import pathlib
import requests
import shutil
import threading
import xml.etree.ElementTree as ET
from google.cloud import storage
from queue import Queue

class LeakyBucketsException(Exception):
    pass

class LeakyBuckets():

    def __init__(self,**kwargs):
        self.download = False
        self.azure_smb = False
        self.queue = Queue()
        self.found = []
        self.alerts = []
        self.azure_storage_accounts = []
        self.__dict__.update(kwargs)

        if not self.keywords and not self.guesses and not self.downloader:
            self.error("Must provide one of the following: --keywords, --guesses, --downloader.")
        
        if (self.keywords and self.guesses) or (self.keywords and self.downloader) or (self.guesses and self.downloader):
            self.error("Cannot provide more than one of the following: --keywords, --guesses, --downloader.")

        if self.keywords:
            if pathlib.Path(self.keywords).is_file():
                with open(self.keywords,"r") as file:
                    self.keywords = file.read().splitlines()
            else:
                self.keywords = self.keywords.split(",")
        elif self.guesses:
            if pathlib.Path(self.guesses).is_file():
                with open(self.guesses,"r") as file:
                    self.guesses = file.read().splitlines()
            else:
                self.guesses = self.guesses.split(",")
        elif self.downloader:
            if pathlib.Path(self.downloader).is_file():
                with open(self.downloader,"r") as file:
                    self.downloader = file.read().splitlines()
            else:
                self.downloader = self.downloader.split(",")  

        if self.az_accounts:
            if pathlib.Path(self.az_accounts).is_file():
                with open(self.az_accounts,"r") as file:
                    self.az_accounts = file.read().splitlines()
            else:
                self.az_accounts = self.az_accounts.split(",")

        if pathlib.Path(self.modifiers).is_file():
            with open(self.modifiers,"r") as file:
                self.modifiers = file.read().splitlines()
        else:
            self.modifiers = self.modifiers.split(",")
            if self.modifiers == ['']:
                self.modifiers = []

    def error(self, error):
        raise LeakyBucketsException(error)

    def guess_gcp(self,guess):
        url = f"https://www.googleapis.com/storage/v1/b/{guess}"
        r = requests.get(f"{url}/iam/testPermissions?permissions=storage.buckets.delete&permissions=storage.buckets.get&permissions=storage.buckets.getIamPolicy&permissions=storage.buckets.setIamPolicy&permissions=storage.buckets.update&permissions=storage.objects.create&permissions=storage.objects.delete&permissions=storage.objects.get&permissions=storage.objects.list&permissions=storage.objects.update")
        if r.status_code == 404:
            pass
        elif r.status_code == 403:
            self.found.append((url,[],"The bucket exists but you do not have access."))
        elif r.json().get("kind"):
            if r.json().get("permissions"):
                perms = ", ".join([perm.split(".")[-1] for perm in r.json().get("permissions")])
                if "list" in perms:
                    files = [(file.name,"") for file in itertools.islice(storage.Client.create_anonymous_client().bucket(guess).list_blobs(),self.max_files)]
                    if self.download:
                        for file,message in files:
                            index = files.index((file,message))
                            files.remove((file,message))
                            dl_folder = '/'.join(url.split("/")[2:]).replace("/","__")
                            if dl_folder.endswith("__"):
                                dl_folder = dl_folder[:-2]
                            if storage.Client.create_anonymous_client().bucket(guess).get_blob(file).size > self.max_size:
                                files.insert(index,(file,"Not saved: File larger than download limit"))
                            else:
                                pathlib.Path(f"./{dl_folder}").mkdir(parents=True, exist_ok=True)
                                file_name = file.split("/")[-1]
                                storage.Client.create_anonymous_client().bucket(guess).blob(file).download_to_filename(f"./{dl_folder}/{file_name}")
                                files.insert(index,(file,f"Saved to: ./{dl_folder}/{file_name}"))
                    self.found.append((url,files, "")) if len(files) > 0 else self.found.append((url,files, "The bucket exists but is empty."))
                elif "create" in perms:
                    self.found.append((url,[], "You have permission to create in this bucket but not to view contents."))
            else:
                self.found.append((url,[],"The bucket exists but you do not have access."))
        else:
            pass

    def guess_aws(self,guess):
        url = f"https://{guess}.s3.amazonaws.com/"
        r = requests.get(url)
        if r.status_code == 404:
            pass
        elif r.status_code == 403:
            self.found.append((url,[],"The bucket exists but you do not have access."))
        elif r.status_code == 200:
            files = [(f.text,"") for f in itertools.islice(ET.fromstring(r.text).iter('{http://s3.amazonaws.com/doc/2006-03-01/}Key'),self.max_files) if not f.text.endswith("/")]
            if self.download:
                for file,message in files:
                    index = files.index((file,message))
                    files.remove((file,message))
                    dl_folder = '/'.join(url.split("/")[2:]).replace("/","__")
                    if dl_folder.endswith("__"):
                        dl_folder = dl_folder[:-2]
                    file_url = f"{url}{requests.utils.quote(file)}"
                    r = requests.head(file_url)
                    if r.status_code == 403:
                        files.insert(index,(file,"Not authorized to access file"))
                    elif int(r.headers["Content-Length"]) > self.max_size:
                        files.insert(index,(file,"Not saved: File larger than download limit"))
                    else:
                        with requests.get(file_url, stream=True) as r:
                            pathlib.Path(f"./{dl_folder}").mkdir(parents=True, exist_ok=True)
                            file_name = file.split("/")[-1]
                            with open(f"./{dl_folder}/{file_name}", 'wb') as f:
                                shutil.copyfileobj(r.raw, f)
                            files.insert(index,(file,f"Saved to: ./{dl_folder}/{file_name}"))
            self.found.append((url,files,"")) if len(files) > 0 else self.found.append((url,files, "The bucket exists but is empty."))
        else:
            pass

    def guess_azure(self,keyword,guess):
        url = f"https://{keyword}.blob.core.windows.net/{guess}"
        try:
            r = requests.get(f"{url}?restype=container&comp=list")
            if r.status_code == 404:
                if keyword not in self.azure_storage_accounts:
                    self.azure_storage_accounts.append(keyword)
                    self.found.append(("/".join(url.split("/")[:-1]),[],"The storage account exists."))
            elif r.status_code == 200:
                files = [(f.text,"") for f in itertools.islice(ET.fromstring(r.text).iter("Name"),self.max_files)]
                if self.download:
                    for file,message in files:
                        index = files.index((file,message))
                        files.remove((file,message))
                        dl_folder = '/'.join(url.split("/")[2:]).replace("/","__")
                        if dl_folder.endswith("__"):
                            dl_folder = dl_folder[:-2]
                        file_url = f"{url}/{requests.utils.quote(file)}"
                        r = requests.head(file_url)
                        if r.status_code == 403:
                            files.insert(index,(file,"Not authorized to access file"))
                        elif int(r.headers["Content-Length"]) > self.max_size:
                            files.insert(index,(file,"Not saved: File larger than download limit"))
                        else:
                            with requests.get(file_url, stream=True) as r:
                                pathlib.Path(f"./{dl_folder}").mkdir(parents=True, exist_ok=True)
                                file_name = file.split("/")[-1]
                                with open(f"./{dl_folder}/{file_name}", 'wb') as f:
                                    shutil.copyfileobj(r.raw, f)
                                files.insert(index,(file,f"Saved to: ./{dl_folder}/{file_name}"))
                self.found.append((url,files,"")) if len(files) > 0 else self.found.append((url,files, "The container exists but is empty."))
        except requests.exceptions.ConnectionError:
            pass

    def download_file(self,url,bucket,file):
        dl_folder = '/'.join(bucket.split("/")[2:]).replace("/","__")
        if dl_folder.endswith("__"):
            dl_folder = dl_folder[:-2]
        if "www.googleapis.com/storage/v1/b" in url:
            bucket_name = url.split("/")[6]
            if storage.Client.create_anonymous_client().bucket(bucket_name).get_blob(file).size > self.max_size:
                return (file,"Not saved: File larger than download limit")
            else:
                pathlib.Path(f"./{dl_folder}").mkdir(parents=True, exist_ok=True)
                file_name = file.split("/")[-1]
                storage.Client.create_anonymous_client().bucket(bucket_name).blob(file).download_to_filename(f"./{dl_folder}/{file_name}")
                return (file,f"Saved to: ./{dl_folder}/{file_name}")
        else:
            r = requests.head(url)
            if r.status_code == 403:
                return (file,"Not authorized to access file")
            elif int(r.headers["Content-Length"]) > self.max_size:
                return (file,"Not saved: File larger than download limit")
            else:
                with requests.get(url, stream=True) as r:
                    pathlib.Path(f"./{dl_folder}").mkdir(parents=True, exist_ok=True)
                    file_name = file.split("/")[-1]
                    with open(f"./{dl_folder}/{file_name}", 'wb') as f:
                        shutil.copyfileobj(r.raw, f)
                    return (file_name,f"Saved to: ./{dl_folder}/{file_name}")

    def worker(self):
        while True:
            if self.keywords or self.guesses:
                guess = self.queue.get()
                if self.alerts:
                    self.queue.task_done()
                    continue
                if len(guess) == 1:
                    self.guess_gcp(guess[0])
                    self.guess_aws(guess[0])
                else:
                    self.guess_azure(guess[0],guess[1])
            elif self.downloader:
                url = self.queue.get()
                if "www.googleapis.com/storage/v1/b" in url:
                    bucket = "/".join(url.split("/")[0:7])
                    file = "/".join(url.split("/")[7:])
                elif ".s3.amazonaws.com" in url:
                    bucket = "/".join(url.split("/")[0:3])
                    file = "/".join(url.split("/")[3:])
                elif ".blob.core.windows.net/" in url:
                    bucket = "/".join(url.split("/")[0:4])
                    file = "/".join(url.split("/")[4:])
                else:
                    self.found.append((url,[],"Are you sure this is the right URL?"))
                file_name,message = self.download_file(url,bucket,file)
                self.found.append((bucket,[(file_name,message)],""))
            self.queue.task_done()

    def prepare(self):    
        if self.keywords:
            for keyword in self.keywords:
                self.queue.put([keyword])
                self.queue.put([keyword,keyword])
                for modifier in self.modifiers:
                    self.queue.put([f"{keyword}{modifier}"])
                    self.queue.put([f"{modifier}{keyword}"])
                    self.queue.put([f"{keyword}-{modifier}"])
                    self.queue.put([f"{keyword}_{modifier}"])
                    self.queue.put([f"{modifier}-{keyword}"])
                    self.queue.put([f"{modifier}_{keyword}"])

                    if self.az_accounts:
                        for account in self.az_accounts:
                            self.queue.put((account,modifier))
                            self.queue.put((account,f"{keyword}{modifier}"))
                            self.queue.put((account,f"{modifier}{keyword}"))
                            self.queue.put((account,f"{keyword}-{modifier}"))
                            self.queue.put((account,f"{keyword}_{modifier}"))
                            self.queue.put((account,f"{modifier}-{keyword}"))
                            self.queue.put((account,f"{modifier}_{keyword}"))
                    else:
                        self.queue.put((keyword,modifier))
                        self.queue.put((keyword,f"{keyword}{modifier}"))
                        self.queue.put((keyword,f"{modifier}{keyword}"))
                        self.queue.put((keyword,f"{keyword}-{modifier}"))
                        self.queue.put((keyword,f"{keyword}_{modifier}"))
                        self.queue.put((keyword,f"{modifier}-{keyword}"))
                        self.queue.put((keyword,f"{modifier}_{keyword}"))
        elif self.guesses:
            for guess in self.guesses:
                self.queue.put([guess])
                if self.az_accounts:
                    for account in self.az_accounts:
                        self.queue.put((account,guess))
                else:
                    self.queue.put((guess,guess))
        elif self.downloader:
            for url in self.downloader:
                self.queue.put(url)

    def go(self):
        
        try:
            workers = [threading.Thread(target=self.worker,args=(),daemon=True) for _ in range(self.threads)]
            [worker.start() for worker in workers]
            self.queue.join()
        except KeyboardInterrupt:
            print("\nTerminating...")
            self.alerts.append("Terminated early due to keyboard interrupt")

        return self.found


if __name__ == "__main__":
        
    import argparse
    parser = argparse.ArgumentParser(description = "Find open storage buckets and accessible files across Amazon Web Services, Google Cloud, and Microsoft Azure simultaneously")
    parser.add_argument(
		"--keywords",
		required=False,
		help="Keywords used to generate guesses. Can be a path to a wordlist file or a comma-separated list of words."
	)
    parser.add_argument(
		"--modifiers",
		required=False,
		help="Used to modify keywords. Can be a path to a wordlist file or a comma-separated list of words.",
        default="./modifiers.txt"
	)
    parser.add_argument(
		"--guesses",
		required=False,
		help="Manually provide guesses. Can be a path to a wordlist file or a comma-separated list of words.",
	)
    parser.add_argument(
		"--downloader",
		required=False,
		help="Provide URLs of files to download. Can be a path to a file or a comma-separated list of URLs.",
	)
    parser.add_argument(
		"--az-accounts",
		required=False,
		help="Provide AZ storage accounts (defaults to either keywords or guesses, whichever is passed in). Can be a path to a wordlist file or a comma-separated list of words.",
	)
    parser.add_argument(
		"--threads",
		required=False,
		help="The max number of threads to use. Defaults to 10.",
		default=10,
		type=int
	)
    parser.add_argument(
		"--max-files",
		required=False,
		help="The max number of items to list/download from each bucket. Defaults to 100.",
		default=10,
		type=int
	)
    parser.add_argument(
		"--max-size",
		required=False,
		help="The max file size (in bytes) to download. Defaults to 100000000.",
		default=100000000,
		type=int
	)
    parser.add_argument(
    "--download",
    required=False,
    help="Automatically download discovered files.",
    action="store_true"
	)
    args = parser.parse_args()

    try:
        leakybuckets = LeakyBuckets(**vars(args))
        if leakybuckets.downloader:
            print("Preparing downloads...")
        else:
            print("Preparing guesses...")
        leakybuckets.prepare()
        print("Making requests...")
        found = leakybuckets.go()

        print("Wrapping up...")

        if len(found) == 0:
            print("Didn't find anything.")
        else:
            for url,files,message in sorted(found,key=lambda vals: len(vals[1])):
                print(f"\n{url}")
                if message:
                    print(f"\t{message}")
                else:
                    for file,message in files:
                        print(f"\t{file}\t({message})") if message else print(f"\t{file}")
                    if len(files) == leakybuckets.max_files:
                        print(f"\t*** Hit max of {leakybuckets.max_files} objects to enumerate per source. There may be more!")
        for alert in leakybuckets.alerts:
            print(f"\n***{alert}")

    except LeakyBucketsException as ex:
        print(ex)