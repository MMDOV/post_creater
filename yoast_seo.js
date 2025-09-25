#!/usr/bin/env node

const { Paper, assessments, assessors, interpreters } = require("yoastseo");
const { getResearcher } = require("./get-researcher.js");

// Assessors
const {
    SEOAssessor,
    ContentAssessor,
    RelatedKeywordAssessor,
    InclusiveLanguageAssessor,
} = assessors;

// Premium assessments
const KeyphraseDistributionAssessment = assessments.seo.KeyphraseDistributionAssessment;
const TextTitleAssessment = assessments.seo.TextTitleAssessment;
const WordComplexityAssessment = assessments.readability.WordComplexityAssessment;
const TextAlignmentAssessment = assessments.readability.TextAlignmentAssessment;

// Map assessment result to a simple object
const resultToVM = (result) => {
    const { _identifier, score, text, marks, editFieldName } = result;
    return { _identifier, score, text, marks, editFieldName, rating: interpreters.scoreToRating(score) };
};

// Main function
async function main() {
    // Read JSON from stdin
    let input = "";
    process.stdin.setEncoding("utf8");
    for await (const chunk of process.stdin) {
        input += chunk;
    }

    let body;
    try {
        body = JSON.parse(input);
    } catch (err) {
        console.error(JSON.stringify({ error: "Invalid JSON input" }));
        process.exit(1);
    }

    const language = body.locale || "en";
    const researcher = getResearcher(language);

    // Instantiate assessors
    const seoAssessor = new SEOAssessor(researcher);
    seoAssessor.addAssessment("keyphraseDistribution", new KeyphraseDistributionAssessment());
    seoAssessor.addAssessment("TextTitleAssessment", new TextTitleAssessment());

    const contentAssessor = new ContentAssessor(researcher);
    contentAssessor.addAssessment("wordComplexity", new WordComplexityAssessment());
    contentAssessor.addAssessment("textAlignment", new TextAlignmentAssessment());

    const relatedKeywordAssessor = new RelatedKeywordAssessor(researcher);
    const inclusiveLanguageAssessor = new InclusiveLanguageAssessor(researcher);

    const paper = new Paper(body.text || "", body);

    // Run assessments
    seoAssessor.assess(paper);
    contentAssessor.assess(paper);
    relatedKeywordAssessor.assess(paper);
    inclusiveLanguageAssessor.assess(paper);

    // Output results
    const result = {
        seo: seoAssessor.getValidResults().map(resultToVM),
        readability: contentAssessor.getValidResults().map(resultToVM),
        relatedKeyword: relatedKeywordAssessor.getValidResults().map(resultToVM),
        inclusiveLanguage: inclusiveLanguageAssessor.getValidResults().map(resultToVM),
    };

    console.log(JSON.stringify(result, null, 2));
}

// Run the CLI
main();

