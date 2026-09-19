"""Verification harness for iterative coding loop."""

from zero_gaze.llm.coder import IterativeCoder

def test_iterative_coder():
    print("--- TESTING ITERATIVE CODER ---")
    coder = IterativeCoder(max_retries=1)
    
    # Ask for a simple script
    paper_context = "Create a python script that prints 'Hello World' and returns a dictionary with key 'Accuracy' and value 100.0. The script must have a syntax error on purpose on the first line, like 'print(missing_var)' so we can test your repair loop."
    
    best_code, result = coder.generate_and_refine(claims=None, paper_context=paper_context)
    
    print(f"Final Success: {result.success}")
    print(f"Final Exit Code: {result.exit_code}")
    print(f"Final Output:\n{result.stdout.strip()}")
    print(f"Final Error:\n{result.stderr.strip()}")
    print("--- END TEST ---")

if __name__ == "__main__":
    test_iterative_coder()