from pathlib import Path
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import letter

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
FONT_ROOT=Path('/usr/share/fonts/truetype/dejavu')
for name,filename in [('Body','DejaVuSans.ttf'),('Body-Bold','DejaVuSans-Bold.ttf'),('Code','DejaVuSansMono.ttf')]:
    pdfmetrics.registerFont(TTFont(name,str(FONT_ROOT/filename)))
pdfmetrics.registerFontFamily('Body',normal='Body',bold='Body-Bold',italic='Body',boldItalic='Body-Bold')

ROOT=Path(__file__).resolve().parent
styles=getSampleStyleSheet()
styles.add(ParagraphStyle(name='MainTitle',fontName='Body-Bold',fontSize=21,leading=25,spaceAfter=12))
styles.add(ParagraphStyle(name='Deck',fontName='Body',fontSize=12,leading=17,spaceAfter=12,textColor=colors.HexColor('#334155')))
styles.add(ParagraphStyle(name='Copy',fontName='Body',fontSize=9.8,leading=13.5,spaceAfter=7))
styles.add(ParagraphStyle(name='Section',fontName='Body-Bold',fontSize=13,leading=17,spaceBefore=9,spaceAfter=6))
styles.add(ParagraphStyle(name='SmallCopy',fontName='Body',fontSize=8.5,leading=12,spaceAfter=6))
story=[]
def p(text,style='Copy'): story.append(Paragraph(text,styles[style]))
def heading(text): p(text,'Section')
def table(headers,rows,widths):
    data=[[Paragraph(str(x),styles['SmallCopy']) for x in headers]]+[[Paragraph(str(x),styles['SmallCopy']) for x in row] for row in rows]
    t=Table(data,colWidths=widths,hAlign='LEFT',repeatRows=1)
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e2e8f0')),('GRID',(0,0),(-1,-1),.4,colors.HexColor('#cbd5e1')),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),8),('RIGHTPADDING',(0,0),(-1,-1),8),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),5)]))
    story.append(t);story.append(Spacer(1,10))
def newpage(): story.append(PageBreak())

p('Evaluating IPAD under<br/>generator shift','MainTitle')
p('An evaluation protocol and accompanying software','Deck')
p('Hongxi Pu | 3 October 2026 | Version 0.1','SmallCopy')
heading('Abstract')
p('A text detector may perform well on one language model and fail on another. This protocol sets out a small, matched evaluation of IPAD under generator shift. The proposed experiment holds the writing domain, source prompts and detector configuration fixed while changing the model that produces the AI text. It measures discrimination, classification performance and false positives on human text, with uncertainty estimated by resampling source groups. The accompanying software evaluates saved detector scores and has passed unit tests and numerical comparisons with an independent implementation. Data collection and IPAD inference remain to be completed; this version reports the experimental design and software checks, with no new detection results.')
heading('1. Research question')
p('How does a fixed IPAD detector perform on a generator outside its original evaluation, when the domain and source prompts are held constant?')
p('The study focuses on generator shift in a single writing domain. This keeps the initial comparison small enough to inspect individual errors and reconstructed prompts. Cross-domain transfer and paraphrasing can be studied in later experiments. The generator and corpus have not yet been selected. Candidate generators will be checked against the original paper and released evaluation data before being described as unseen.')
heading('2. Connection to IPAD')
p('IPAD uses inverse prompts and consistency-based signals to detect AI-generated text [1]. This study will examine the transfer of a fixed IPAD configuration. Reconstructed prompts will also be inspected to understand what information the detector recovers from a passage and how that information changes across generators.')
p('Detection performance and explanation quality are separate questions. A plausible reconstructed prompt may help describe a decision, but it does not by itself establish the source of a text or the faithfulness of an explanation. The initial study therefore treats these examples as qualitative observations.')
heading('Scope of this version')
p('The completed work consists of this protocol, inspection of the public model resources and a saved-score evaluator. The evaluator has passed 12 unit tests and 200 numerical cross-checks. The remaining experimental work is to select the data and generator, verify the inference pipeline and collect predictions.')
p('Code and supporting files: <link href="https://github.com/p123hx/ipad-robustness" color="#1d4ed8">github.com/p123hx/ipad-robustness</link>.','SmallCopy')

newpage()
p('Experimental design','MainTitle')
heading('3. Matched source groups')
p('The proposed pilot uses 150 source groups from one corpus with documented provenance and suitable reuse terms. Each group consists of a source prompt and a human-written response. Fifty groups are assigned to source validation and 100 to held-out testing before text generation. All passages derived from the same prompt or source document remain in the same split. Exact and near-duplicate checks are applied before the split is finalized.')
table(['Condition','Human / AI records','Role'],[
('Source validation: 50 groups','50 / 50','Check source settings and select a threshold if calibration is needed.'),
('Reference-generator test: 100 groups','100 / 100','Evaluate the fixed detector on the reference condition.'),
('Shifted-generator test: the same 100 groups','100 / 100','Change the generator using matched prompts and human controls.')],[187,100,217])
p('Reusing the 100 human test passages across the two conditions gives 500 evaluation rows from 400 distinct texts. Shared group identifiers preserve the pairing. Metrics are reported separately for each condition, so reused human passages are not counted twice in a pooled estimate. These counts define a pilot; a formal power analysis has not been conducted.')
heading('4. Fixed detector configuration')
p('The base model, adapters, tokenizer, prompt templates, numerical precision, maximum lengths and score aggregation are fixed across test conditions. The regeneration model and its settings are also held constant. The decision threshold is taken from a documented original setting or selected using source validation alone, before shifted-test scores are inspected.')
p('The experiment records generator versions, sampling parameters, generation dates, corpus revisions, source identifiers and text hashes. Any change to a published inference setting is recorded with the resulting configuration.')
heading('5. Scores and failure records')
p('The evaluator expects a continuous score in [0,1], with higher values indicating AI-generated text. Score direction, normalization and yes/no token handling must be verified in the inference pipeline. Component scores, reconstructed prompts and regenerated passages are retained with their sample identifiers.')
p('A manifest records every attempted sample and any inference failure. Missing predictions are resolved or reported with the achieved coverage. They are not silently excluded from the evaluation.')
heading('6. Qualitative inspection')
p('A small set of source groups will be selected before reviewing the detector outputs. For both generator conditions, the analysis will examine prompt relevance and the consistency signals used by the detector. These observations will be reported alongside errors, including cases where a convincing reconstruction accompanies an incorrect classification.')

newpage()
p('Evaluation and software checks','MainTitle')
heading('7. Metrics and uncertainty')
p('The evaluator reads sample_id, group_id, split, condition, label and score from a CSV file. For each test condition, it computes accuracy, precision, recall, F1, human-text false-positive rate and AUROC. A score greater than or equal to the supplied threshold is classified as AI-generated. AUROC assigns average ranks to tied scores; undefined metrics are returned as null.')
p('Confidence intervals use a cluster bootstrap over source groups. All rows belonging to a sampled group are retained together. The software reports 95% percentile intervals, the random seed and the number of usable replicates. It withholds intervals when too few replicates are valid. This version estimates each condition separately; paired intervals for performance differences are left for a later extension.')
heading('8. Software validation')
table(['Check','Outcome'],[
('Unit tests','12 passed, covering ranking and ties, threshold boundaries, undefined metrics, duplicate identifiers, split leakage, invalid scores, repeatability and required study metadata.'),
('Independent metric comparison','AUROC, accuracy and F1 agreed with scikit-learn 1.8.0 across 200 artificial cases, with absolute tolerance 1e-12.'),
('Example execution','The complete evaluator ran on 8 numerical test rows with 2,000 group-bootstrap draws.')],[180,324])
p('The test inputs are artificial labels and scores. They check the evaluator, not the IPAD detector, and contain no human-written or model-generated passages. The repository keeps these outputs under software-validation to distinguish them from future experimental results.')
heading('Running the checks')
p('<font face="Code" size="8">python3 -m unittest discover -s tests -v</font>')
p('<font face="Code" size="8">python3 evaluate.py --predictions examples/fixture_predictions.csv<br/> --metadata examples/fixture_metadata.json --threshold 0.5<br/> --purpose software-validation --bootstrap 2000<br/> --out validation/fixture_metrics.json</font>')
p('The second command is shown across lines for readability; the README provides a copyable shell command. The threshold 0.5 is a test setting. Evaluation of real predictions requires a separately documented threshold and completed study metadata. The evaluator uses Python 3.10 or later and the standard library.')
heading('Validation limits')
p('Input checks detect missing scores, duplicate row identifiers, declared split leakage and mismatches with the expected row count. They cannot verify human authorship, identify every duplicate passage or establish the absence of training overlap. Those checks depend on the corpus and inference records.')

newpage()
p('Implementation notes and outlook','MainTitle')
heading('9. Reproducing the inference pipeline')
p('The public IPAD model repository provides adapters and test resources [2], linked from the code repository [3]. It uses Phi-3-medium-128k-instruct as the base model [4]. The score evaluator is independent of this inference stack and does not load model weights.')
p('Source inspection identified several details to resolve before inference. The model-card comments and paper appear to use the PTCV and RC names differently. The two helper script names also do not clearly describe their contents, and probability extraction uses a local file produced by a customized inference engine. The adapter mapping, training formats and sample-to-score correspondence will therefore be checked on a small set of known inputs before collecting the test predictions. These observations concern reproduction details; they do not assess the published results.')
heading('10. Planned analysis')
p('After selecting a corpus and a new generator, the next step is to verify the full pipeline, including reconstruction, regeneration and score combination. The source groups, generation settings and decision threshold will then be fixed for the held-out evaluation.')
p('The analysis will compare performance across the matched generator conditions and examine individual errors. Because the human controls and detector are shared, their false-positive rate should be unchanged under deterministic scoring; any difference would prompt a check of the execution settings. Changes in AI-text recall and AUROC will help identify whether the detector transfers to the new generator.')
p('Later experiments may extend the design to a second domain or to paraphrased text. Uncertainty-aware decisions and more systematic evaluation of reconstructed prompts are further directions. Their usefulness will depend on the errors observed in the initial study.')
heading('References')
p('[1] Chen et al. IPAD: Inverse Prompt for AI Detection - A Robust and Interpretable LLM-Generated Text Detector. NeurIPS 2025. <link href="https://proceedings.nips.cc/paper_files/paper/2025/hash/f4d6932b6b9eec9b9d595e2847d095c1-Abstract-Conference.html" color="#1d4ed8">Proceedings record</link>.','SmallCopy')
p('[2] IPAD model resources. <link href="https://huggingface.co/bellafc/IPAD" color="#1d4ed8">huggingface.co/bellafc/IPAD</link>.<br/>Revision inspected: e57952ab8f36a77421a02f96ac2a2fa13d324b6e.','SmallCopy')
p('[3] IPAD code repository. <link href="https://github.com/Bellafc/IPAD-Inver-Prompt-for-AI-Detection" color="#1d4ed8">github.com/Bellafc/IPAD-Inver-Prompt-for-AI-Detection</link>.<br/>Accessed 3 October 2026.','SmallCopy')
p('[4] Phi-3-medium-128k-instruct. <link href="https://huggingface.co/microsoft/Phi-3-medium-128k-instruct" color="#1d4ed8">Microsoft model repository</link>.<br/>Revision inspected: a088b37c71d441ab6d862bb3fcfe6165b3014702.','SmallCopy')
p('Acknowledgment: AI tools assisted with drafting and software development.','SmallCopy')

def footer(c,doc):
    c.saveState();c.setFont('Body',8);c.setFillColor(colors.HexColor('#64748b'))
    c.drawString(54,30,'IPAD evaluation protocol | Work in progress | 2026-10-03')
    c.drawRightString(558,30,str(doc.page));c.restoreState()

SimpleDocTemplate(str(ROOT/'IPAD_Robustness_Protocol.pdf'),pagesize=letter,
                 leftMargin=54,rightMargin=54,topMargin=46,bottomMargin=48,
                 title='Evaluating IPAD under generator shift',author='Hongxi Pu').build(story,onFirstPage=footer,onLaterPages=footer)
