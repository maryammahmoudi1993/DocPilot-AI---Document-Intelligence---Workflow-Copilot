const SUGGESTIONS = [
  'What is the total on the most recent invoice?',
  'Summarize the key terms of the contract.',
  'Which documents mention a discount?',
  'Are there any overdue payments?',
];

export interface SuggestedQuestionsProps {
  onSelect: (question: string) => void;
}

export function SuggestedQuestions({ onSelect }: SuggestedQuestionsProps) {
  return (
    <div className="flex flex-wrap gap-2">
      {SUGGESTIONS.map((question) => (
        <button
          key={question}
          type="button"
          onClick={() => onSelect(question)}
          className="rounded-full border border-border bg-card px-3 py-1.5 text-xs text-text-secondary transition-colors duration-fast hover:bg-lavender hover:text-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
        >
          {question}
        </button>
      ))}
    </div>
  );
}
