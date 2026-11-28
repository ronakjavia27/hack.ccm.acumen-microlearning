# Studio inbox

Default inbox when `STUDIO_INPUT_DIR` is not set. On the laptop hub, point `STUDIO_INPUT_DIR` at your
Google Drive for desktop folder instead (docs/console/REMOTE_ACCESS.md).

```
CCM/ Medicine/ Microbiology/
  <topic>.md | .docx | .txt | .pdf   → NOTE: one item; your note becomes the theory section,
                                        Q&A + flashcards + MCQs are derived from it
  Questions/<paper>.txt | .md | .docx | .pdf | .csv   → QUESTION LIST: one item per question
Processed/                            ← ingested files are moved here
```
Re-saving a note under the same file name creates a new version of the same item.

Question-list format:
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

Run: `python studio.py watch` (background) or `python studio.py run` (once) → review at /console/studio.
