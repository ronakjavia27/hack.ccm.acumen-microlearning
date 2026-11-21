# Studio input — drop question lists here

Put files under the subject folder: `Medicine/`, `Microbiology/` or `CCM/` (sub-folders are fine).
Formats: `.txt` `.md` `.docx` `.pdf` `.csv`.

```
1. Discuss the pathophysiology and management of ARDS. (10 marks)
2. Short note: procalcitonin-guided antibiotic stewardship (5)
3. Viva: what is the Surviving Sepsis hour-1 bundle?
4. Gram-negative intracellular diplococci in CSF suggest:
   a) S. pneumoniae
   b) N. meningitidis
   c) H. influenzae
   d) Listeria
   Ans: b
```
CSV header: `question,marks,type,system,subtopic,source,option_a,option_b,option_c,option_d,answer`

Then: `python studio.py run` → review at http://localhost:8878/console/studio → `python studio.py publish`.
