"""Build the report from the committed corpus audit and design calculations."""
import json
from pathlib import Path
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

ROOT=Path(__file__).resolve().parent
FONT_ROOT=Path('/usr/share/fonts/truetype/dejavu')
for name,filename in [('Body','DejaVuSerif.ttf'),('Body-Bold','DejaVuSerif-Bold.ttf'),('Code','DejaVuSansMono.ttf')]:
    pdfmetrics.registerFont(TTFont(name,str(FONT_ROOT/filename)))
pdfmetrics.registerFontFamily('Body',normal='Body',bold='Body-Bold',italic='Body',boldItalic='Body-Bold')
styles=getSampleStyleSheet()
for name,size,leading,after in [('TitleText',19,24,10),('Copy',10,14,7),('Section',12,16,7),('Small',8.3,11.5,6),('Equation',10,16,9)]:
    styles.add(ParagraphStyle(name=name,fontName='Body-Bold' if name in ['TitleText','Section'] else 'Body',fontSize=size,leading=leading,spaceAfter=after,spaceBefore=5 if name=='Section' else 0))
audit=json.loads((ROOT/'analysis/corpus_audit.json').read_text())
calc=json.loads((ROOT/'analysis/design_calculations.json').read_text())
check=json.loads((ROOT/'validation/independent_crosscheck.json').read_text())
story=[]
def p(s,style='Copy'):story.append(Paragraph(s,styles[style]))
def h(s):p(s,'Section')
def page():story.append(PageBreak())
def table(headers,rows,widths):
    t=Table([[Paragraph(str(x),styles['Small']) for x in r] for r in [headers]+rows],colWidths=widths,repeatRows=1,hAlign='LEFT')
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#eeeeee')),('LINEBELOW',(0,0),(-1,0),.6,colors.grey),('LINEBELOW',(0,-1),(-1,-1),.4,colors.grey),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),7),('RIGHTPADDING',(0,0),(-1,-1),7),('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6)]))
    story.append(t);story.append(Spacer(1,9))

p('Evaluating IPAD under generator shift','TitleText')
p('Matched-source protocol, corpus audit, and statistical design')
p('Hongxi Pu · 6 October 2026 · Version 0.2','Small')
h('Abstract')
p('A detector can preserve the ordering of human and generated texts while losing recall at its deployed decision threshold. This note develops a matched evaluation of that distinction for IPAD. An audit of the released OUTFOX test resources recovers 500 human–reference pairs by their source prompts; only 492 pairs align by row position. The software constructs a reproducible source manifest, estimates paired changes in recall and AUROC, and checks that shared human controls receive identical scores. An exact binomial calculation shows why the original 100-human pilot cannot, even with zero observed errors, support a 1% false-positive-rate claim at one-sided 95% confidence. The revised design reserves 300 groups for evaluation. Completed results concern corpus correspondence and statistical design; IPAD inference and generation of the shifted corpus remain to be performed.')
h('1. Question and scope')
p('With the task, prompts, detector and threshold held fixed, how much does detection change when the generating model changes? Two quantities answer different parts of this question: AUROC measures ranking across human and AI texts; AI recall measures the fraction of generated texts exceeding a fixed threshold. The study will estimate changes in both, rather than treating a high AUROC as evidence that the deployed threshold transfers.')
p('IPAD reconstructs a prompt and combines prompt–text consistency and regenerated-text comparison [1]. This follow-up evaluates that published detector. It does not introduce a replacement detector or claim a new statistical method. Its present contribution is an auditable evaluation design and implementation tied to specific public inputs.')
h('2. Public inputs and correspondence')
p('The audit reads <font face="Code" size="8.3">test_outfox.csv</font> and <font face="Code" size="8.3">test_human_outfox.jsonl</font> from the pinned IPAD model repository [2]. It joins the CSV’s <font face="Code" size="8.3">expected_output</font> to the JSONL’s <font face="Code" size="8.3">output</font> after whitespace normalization; these fields contain the problem statements. The respective <font face="Code" size="8.3">input</font> fields supply the passages. The CSV’s <font face="Code" size="8.3">predicted_output</font> is not used as a detection score.')
table(['Executed check','Result'],[
['Rows in each file',f"{audit['ai_file_rows']} reference; {audit['human_file_rows']} human"],
['Unique prompt matches after joining',audit['matched_prompts']],
['Prompt matches at the same row position',audit['positional_prompt_matches']],
['Unique passage hashes within each label',f"{audit['unique_reference_texts']} reference; {audit['unique_human_texts']} human"],
['Exact passage overlap across labels',audit['cross_label_exact_text_overlap']]], [330,174])

page()
h('2.1. Independent source check')
p('The joined records were checked against the original OUTFOX repository [3]: all 500 human passages match exactly; 498 reference passages match exactly and all 500 match after whitespace normalization. The remaining two differ only by carriage-return characters. Thus, matching by prompt recovers the source correspondence even where the file orders differ. This observation does not imply that the original IPAD experiments paired these files by row number.')
p('The reference texts come from OUTFOX’s released ChatGPT test set. Their collection predates this note. The new artifact is the correspondence audit and split manifest, not a newly collected corpus. Existing labels and provenance are inherited from the releases; exact matches do not establish authorship independently, rule out near duplicates, or demonstrate that the passages were absent from IPAD training.')
h('3. Sampling and execution plan')
p('The 500 matched prompts are ordered by a salted SHA-256 hash, without consulting detector scores. The first 100 groups are assigned to development, the next 300 to the planned test, and the last 100 to reserve. The manifest records source row numbers, prompt and passage hashes, and word counts. This is a follow-up analysis split of an existing public test set, not a claim that the reference data were previously unseen by IPAD.')
table(['Partition','Groups','Planned use'],[
['Development',100,'Verify module mapping, token handling and sample alignment.'],
['Matched test',300,'One existing human and reference text, plus one new generation per prompt.'],
['Reserve',100,'Unexamined backup for a separately documented extension; no replacement based on detector outcomes.']], [100,55,349])
p('The intended next experiment adds one generator using the original OUTFOX generation contexts, which include the problem statement and requested essay length. All 500 contexts were recovered and matched to their problem statements; their hashes are in the manifest. The new model revision, system message, sampling settings, output limit and collection date must be recorded before scoring. No additional generator has yet been selected or tested.')
p('For the 300 test groups, there will be 900 distinct passages: 300 human, 300 existing reference and 300 new generated texts. The two human-versus-AI conditions contain 1,200 evaluation rows because the same 300 human scores appear in both. They must not be pooled as 600 independent human observations.')
h('3.1. What remains controlled')
p('The detector configuration, inverse-prompt template, tokenizer, truncation, precision and regeneration settings remain fixed. Human passages are scored once and reused. Attempts and failures are logged; incomplete pairs are rejected. Topic, near-duplicate and length checks precede inference. This compares a historical reference with a new generation condition: if original system messages or sampling settings cannot be recovered, differences cannot be attributed solely to the model. A controlled model-only comparison would require regenerating both conditions under documented common settings.')

page()
h('4. Scores, estimands and paired uncertainty')
p('The published IPAD configuration combines the two normalized yes/no component scores as s = 0.45 p<sub>PTCV</sub> + 0.55 p<sub>RC</sub>, with AI predicted when s &gt; 0.54 [1, §2.2]. The default evaluation rule now uses this strict inequality. A configurable ≥ rule is retained for other score sources, and the chosen rule is written into the output. These published settings become reproduction settings only after the component mapping and score extraction have been verified.')
p('The primary contrasts are shifted-generator minus reference-generator AI recall at the fixed threshold, and shifted minus reference AUROC. Lower values indicate degradation. Accuracy, F1 and human false-positive rate are supplementary summaries. Because both conditions contain the same number of human and AI texts and share identical human predictions, the following are exact sample identities:','Copy')
p('ΔFPR = 0, &nbsp;&nbsp; ΔAccuracy = ½ ΔRecall.','Equation')
p('These identities are diagnostic checks, not evidence that false positives cannot occur in a new domain. They hold because the human controls are deliberately shared. AUROC is computed from continuous scores with half credit for ties, not from thresholded binary labels.')
p('For uncertainty, the software samples source-group identifiers with replacement and carries all four rows of each sampled group into both conditions. It recomputes each metric and its difference for 2,000 draws, then reports the 2.5th and 97.5th percentiles. Resampling the conditions independently would discard their pairing. Intervals are conditional on the frozen detector, chosen threshold and collected generations; they do not include variability from retraining, selecting a threshold or repeatedly sampling the generator.')
p('The paired implementation requires both labels in both conditions for every source group, identical human text identifiers and scores across conditions, and unique human identifiers across groups. It refuses to silently discard unmatched rows. Degenerate bootstrap distributions are flagged; a point interval should not be interpreted as universal certainty.')
h('4.1. Why ranking and a threshold must be checked separately')
p('A constructed score example makes the distinction explicit. For 100 groups, let human scores range from 0.10 to 0.30, reference AI scores from 0.70 to 0.90, and shifted AI scores from 0.35 to 0.50. Every AI score exceeds every human score in both conditions, so both AUROCs equal 1. At the fixed threshold 0.54, however, AI recall changes from 1 to 0. The code reproduces this example and the exact accuracy identity above.')
p('These are deliberately constructed numbers, not outputs of IPAD. The example establishes a logical limitation of using AUROC alone; it does not predict the magnitude or direction of IPAD’s behavior on a future generator.')
h('4.2. Interpretable evidence')
p('For 20 test groups selected by manifest order before inference, retain the reconstructed prompts, both component scores and final decisions. Describe off-topic, overly generic or unsupported reconstructions, including incorrect decisions with plausible explanations. These annotations are exploratory. Fluency or plausibility of a recovered prompt is not itself a measurement of explanation faithfulness.')

page()
h('5. How many human controls are informative?')
p('A bootstrap cannot create an error that never occurred: if all sampled human scores are below the threshold, every ordinary bootstrap resample has zero false positives. Its apparent interval [0, 0] therefore gives no useful upper bound on a rare unseen error rate. For independent representative human examples at a fixed threshold, use a binomial upper confidence bound [4].')
p('Let X be the number of false positives among n human texts. If X = 0, then P(X = 0 | p) = (1 − p)<super>n</super>. Solving this expression at α = 0.05 gives the one-sided 95% upper bound','Copy')
p('p<sub>upper</sub> = 1 − 0.05<super>1/n</super>.','Equation')
table(['Independent human texts','Upper FPR if zero errors','P(zero errors) if true FPR is 1%'],
      [[r['n_independent_humans'],f"{100*r['one_sided_95pct_fpr_upper']:.3f}%",f"{100*r['probability_zero_errors_if_true_fpr_1pct']:.3f}%"] for r in calc['zero_error_bounds']], [160,150,194])
p('The original plan’s 100 human controls would yield a 2.951% upper bound, even in the best observed case of zero errors. At least 299 independent human observations with zero errors are required to bring this particular bound to 1% or below. The revised test size is 300 for that reason. For a 0.1% bound, the corresponding minimum is 2,995. These are conditional zero-error calculations, not a power analysis or a promise that the detector will attain either target.')
p('For k &gt; 0 false positives, the implementation solves the exact binomial-tail equation for the upper limit. The same 300 human controls supply one FPR estimate shared by both generator conditions. If the corpus contains dependent essays from the same author or source, the independence assumption must be revisited; treating every row as an independent observation would overstate precision.')
h('5.1. Interpretation of the completed analysis')
p('The source audit establishes that a concrete matched corpus can be assembled from the public files and identifies how to join it correctly. The statistical analysis changes the pilot design in two ways: compare the conditions with paired resampling, and enlarge the human control set before attempting a low-FPR claim. Neither calculation establishes the detector’s actual robustness.')
p('The eventual empirical report should give the number attempted, number scored, shared-human false positives with their denominator and bound, both primary contrasts with intervals, and the component-score diagnostics. A small or uncertain difference would be reported as such. A failure of the fixed threshold despite stable AUROC would motivate calibration work; deterioration in both would motivate investigation of the underlying detection signals.')

page()
h('6. Reproducibility and verification')
p('The repository contains the audit script, a 500-group hash manifest, statistical utilities, evaluator, constructed examples, tests and this report’s build source. Raw third-party passages and model weights are not redistributed. Source URLs, immutable revisions and SHA-256 file digests are recorded in <font face="Code" size="8.3">analysis/corpus_audit.json</font>.')
table(['Executed verification','Outcome'],[
['Regression suite','23 tests passed: joins, ambiguous prompts, incomplete pairs, shared controls, boundary rules, metrics, leakage and invalid inputs.'],
['Metrics versus scikit-learn',f"{check['metric_cases']} randomized cases; maximum absolute error {check['metric_max_abs_error']:.2g}."],
['Exact bounds versus SciPy',f"{check['exact_bound_cases']} cases, including boundary counts; maximum error {check['bound_max_abs_error']:.2g}."],
['Paired intervals versus independent calculation',f"{check['paired_bootstrap_draws']} identical group draws; NumPy quantiles and scikit-learn metrics agree within {check['paired_interval_max_abs_error']:.2g}."]], [171,333])
p('Reproduce the corpus audit with <font face="Code" size="8.3">python3 audit_corpus.py --download</font>, the exact calculations with <font face="Code" size="8.3">python3 design_analysis.py</font>, and the numerical checks with <font face="Code" size="8.3">python3 validate_numerics.py</font>. The README provides the full paired-evaluation command. Evaluation and auditing use Python’s standard library; independent validation uses NumPy 2.3.5, SciPy 1.17.0 and scikit-learn 1.8.0. PDF generation uses ReportLab 4.4.9.')
h('6.1. Remaining work and limits')
p('End-to-end IPAD inference has not been run for this follow-up. The checkpoint-to-module mapping, score extraction, regeneration setup and any necessary substitutions must be validated on development data first. The current software evaluates saved scores; it is not an inference implementation. The next deliverable is a versioned run configuration and scored manifest for the additional generator, followed by the paired analysis specified here.')
p('This is a preliminary methods note and evaluation protocol. It reports a data correspondence audit and established statistical calculations, not a new detector, peer-reviewed finding or completed generator-shift benchmark. AI tools assisted with code and drafting.')
h('References and source records')
p('[1] Chen, Z., et al. IPAD: Inverse Prompt for AI Detection — A Robust and Interpretable LLM-Generated Text Detector. NeurIPS 2025, §2.2, pp. 3–4. https://doi.org/10.52202/085713-5580','Small')
p('[2] IPAD model and test resources. https://huggingface.co/bellafc/IPAD<br/>Revision: e57952ab8f36a77421a02f96ac2a2fa13d324b6e. Files and digests are listed in the accompanying audit output. Retrieved 6 October 2026.','Small')
p('[3] Koike, R., Kaneko, M., and Okazaki, N. OUTFOX: LLM-Generated Essay Detection Through In-Context Learning with Adversarially Generated Examples. AAAI 2024. https://doi.org/10.1609/aaai.v38i19.30120<br/>Source: https://github.com/ryuryukke/OUTFOX<br/>Revision: 8dd6bfdec8e24ff6aeecae3015ab663f257e0350.','Small')
p('[4] NIST Dataplot. Exact Binomial Confidence Limits.<br/>https://itl.nist.gov/div898/software/dataplot/refman2/auxillar/exacbino.htm','Small')
p('Code and report: https://github.com/p123hx/ipad-robustness<br/>Earlier protocol record: https://zenodo.org/records/23120967<br/>This revision is dated 6 October 2026; the earlier Zenodo record does not by itself archive this revision.','Small')

def footer(c,doc):
    c.saveState();c.setFont('Body',8);c.setFillColor(colors.grey)
    c.drawString(54,29,'IPAD evaluation protocol · Version 0.2 · 6 October 2026')
    c.drawRightString(558,29,str(doc.page));c.restoreState()

if __name__=='__main__':
    SimpleDocTemplate(str(ROOT/'IPAD_Robustness_Protocol.pdf'),pagesize=letter,
        leftMargin=54,rightMargin=54,topMargin=43,bottomMargin=47,
        title='Evaluating IPAD under generator shift',author='Hongxi Pu').build(story,onFirstPage=footer,onLaterPages=footer)
