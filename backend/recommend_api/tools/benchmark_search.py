# benchmark search script
import requests, time, statistics

BASE_URL = "http://127.0.0.1:8000/api/v1/search"

TIMEOUT = 5 # seconds

TASKS = [{
    "search_type": "track",
    "description": "3 char search (LIKE)",
    "queries": ["met", "dre", "dio", "dna", "the", "wal", "3fd"]
}, {
    "search_type": "track",
    "description": "one word search (FTS + TrigramWordDistance)",
    "queries": ["mozart", "adele", "hello", "rihanna", "umbrela", "beyond", "fsdfsdfsdf"]
},{
    "search_type": "track",
    "description": "multi word search (FTS + TrigramDistance)",
    "queries": [
        "master of puppets", "smells like teen spirit", "ok compter", "lose yourself",
        "hotline bling", "the beatles", "jbdf saz bqrt"
    ]
}, {
    "search_type": "artist",
    "description": "3 char search (LIKE)",
    "queries": ["que", "abb", "emi", "nir", "dra", "met", "xqz"]
}, {
    "search_type": "artist",
    "description": "one word search (TrigramDistance)",
    "queries": ["queen", "abba", "eminem", "nirvana", "metalica", "drake", "qxyzmgfgd"]
}, {
    "search_type": "album",
    "description": "3 char search (LIKE)",
    "queries": ["thr", "abb", "rum", "rev", "hyb", "bac", "z9q"]
}, {
    "search_type": "album",
    "description": "one word search (TrigramDistance)",
    "queries": ["thriler", "back", "rumours", "revival", "hybrid", "abbey", "qxyzmgfgd"]
}]

def run_benchmark():
    for task in TASKS:
        print(f"{task["search_type"]} search with {task["description"]}")
        response_times = []

        for i in range(len(task["queries"])):
            query = task["queries"][i]
            params = {
                "q": query,
                "type": task["search_type"],
                "limit": 50
            }

            try:
                start = time.perf_counter()
                response = requests.get(BASE_URL, params=params)
                elapsed = time.perf_counter() - start


                if response.status_code == 200:
                    response_times.append(elapsed)
                    print(f"    [{i+1}][{query}] OK {elapsed:.4f}s")
                else:
                    print(f"    [{i+1}][{query}] FAIL {response.status_code}")

            except requests.exceptions.RequestException as e:
                print(f"    [{i+1}][{query}] ERROR {e}")

        if response_times:
            print(f"Average: {statistics.mean(response_times):.4f}s")
            print(f"Median:  {statistics.median(response_times):.4f}s")


if __name__ == "__main__":
    run_benchmark()