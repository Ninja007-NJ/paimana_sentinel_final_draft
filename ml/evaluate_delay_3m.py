"""Reload and print the frozen temporal-test evaluation produced by training."""
import json
from ml.config import REPORT_DIR


def main():
    result=json.loads((REPORT_DIR/"training_result.json").read_text(encoding="utf-8"))
    print(json.dumps(result,indent=2))


if __name__=="__main__": main()
