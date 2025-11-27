import type { Question } from '../types';

export const QUESTION_STATUS = {
  NOT_ANSWERED: 'not_answered',
  ANSWERED: 'answered',
  MARKED: 'marked'
} as const;

export const TIMER_DURATION = 60 * 60; // 60 minutes in seconds

export const MOCK_QUESTIONS: Question[] = [
  {
    id: 1,
    topic: 'LLMs',
    question: 'What does GPT stand for in GPT-4?',
    options: ['General Purpose Transformer', 'Generative Pre-trained Transformer', 'Generalized Predictive Text', 'Global Processing Technology'],
    correctAnswer: 1
  },
  {
    id: 2,
    topic: 'Neural Networks',
    question: 'What is the primary innovation of the Transformer architecture?',
    options: ['Convolutional layers', 'Attention mechanism', 'Recurrent connections', 'Pooling layers'],
    correctAnswer: 1
  },
  {
    id: 3,
    topic: 'Tokenization',
    question: 'What is tokenization in the context of language models?',
    options: ['Converting text to numbers', 'Breaking text into smaller units', 'Encrypting text', 'Compressing text'],
    correctAnswer: 1
  },
  {
    id: 4,
    topic: 'Prompt Engineering',
    question: 'What is few-shot learning in prompt engineering?',
    options: ['Training with few examples', 'Providing examples in the prompt', 'Using few parameters', 'Training for few epochs'],
    correctAnswer: 1
  },
  {
    id: 5,
    topic: 'RAG',
    question: 'What does RAG stand for in AI?',
    options: ['Random Access Generation', 'Retrieval Augmented Generation', 'Recursive Algorithm Generation', 'Real-time Adaptive Generation'],
    correctAnswer: 1
  },
  {
    id: 6,
    topic: 'Fine-tuning',
    question: 'What is fine-tuning in the context of LLMs?',
    options: ['Adjusting model parameters for specific tasks', 'Reducing model size', 'Speeding up inference', 'Changing model architecture'],
    correctAnswer: 0
  },
  {
    id: 7,
    topic: 'Attention Mechanism',
    question: 'What is self-attention in Transformers?',
    options: ['Attention to external data', 'Attention between different sequences', 'Attention within the same sequence', 'Attention to user input'],
    correctAnswer: 2
  },
  {
    id: 8,
    topic: 'Model Architecture',
    question: 'What is the difference between encoder and decoder in Transformers?',
    options: ['Encoder reads input, decoder generates output', 'Encoder generates, decoder reads', 'Both are identical', 'Encoder is for training, decoder for inference'],
    correctAnswer: 0
  },
  {
    id: 9,
    topic: 'Embeddings',
    question: 'What are word embeddings?',
    options: ['Text compression technique', 'Dense vector representations of words', 'Word frequency counts', 'Text encoding methods'],
    correctAnswer: 1
  },
  {
    id: 10,
    topic: 'Model Training',
    question: 'What is the purpose of a learning rate in neural network training?',
    options: ['Control training speed', 'Determine model size', 'Set number of epochs', 'Choose activation function'],
    correctAnswer: 0
  },
  {
    id: 11,
    topic: 'LLMs',
    question: 'What is the main advantage of large language models?',
    options: ['Faster inference', 'Better generalization from pre-training', 'Smaller memory footprint', 'Simpler architecture'],
    correctAnswer: 1
  },
  {
    id: 12,
    topic: 'Prompt Engineering',
    question: 'What is chain-of-thought prompting?',
    options: ['Linking multiple prompts', 'Breaking down reasoning steps', 'Using sequential models', 'Connecting different models'],
    correctAnswer: 1
  },
  {
    id: 13,
    topic: 'Model Evaluation',
    question: 'What does BLEU score measure?',
    options: ['Model accuracy', 'Text generation quality', 'Translation quality', 'Model speed'],
    correctAnswer: 2
  },
  {
    id: 14,
    topic: 'Neural Networks',
    question: 'What is the purpose of the softmax function?',
    options: ['Normalize inputs', 'Convert logits to probabilities', 'Activate neurons', 'Reduce overfitting'],
    correctAnswer: 1
  },
  {
    id: 15,
    topic: 'RAG',
    question: 'What is the main benefit of RAG over fine-tuning?',
    options: ['Faster training', 'Access to external knowledge without retraining', 'Smaller models', 'Better accuracy'],
    correctAnswer: 1
  },
  {
    id: 16,
    topic: 'Tokenization',
    question: 'What is a subword tokenization method used in modern LLMs?',
    options: ['Word-level tokenization', 'Character-level tokenization', 'Byte Pair Encoding (BPE)', 'Sentence-level tokenization'],
    correctAnswer: 2
  },
  {
    id: 17,
    topic: 'Model Architecture',
    question: 'What is the purpose of positional encoding in Transformers?',
    options: ['Reduce model size', 'Provide sequence order information', 'Improve attention', 'Speed up training'],
    correctAnswer: 1
  },
  {
    id: 18,
    topic: 'Fine-tuning',
    question: 'What is LoRA in the context of fine-tuning?',
    options: ['Low-Rank Adaptation', 'Large Output Response Algorithm', 'Linear Optimization Routine', 'Learning Rate Adjustment'],
    correctAnswer: 0
  },
  {
    id: 19,
    topic: 'Prompt Engineering',
    question: 'What is the zero-shot learning approach?',
    options: ['Training without data', 'Inference without examples in prompt', 'Using zero parameters', 'Training for zero epochs'],
    correctAnswer: 1
  },
  {
    id: 20,
    topic: 'Model Training',
    question: 'What is gradient descent?',
    options: ['Optimization algorithm', 'Data preprocessing method', 'Model architecture', 'Evaluation metric'],
    correctAnswer: 0
  },
  {
    id: 21,
    topic: 'LLMs',
    question: 'What is the difference between GPT and BERT?',
    options: ['GPT is decoder-only, BERT is encoder-only', 'GPT is encoder-only, BERT is decoder-only', 'Both are identical', 'GPT is for classification, BERT for generation'],
    correctAnswer: 0
  },
  {
    id: 22,
    topic: 'Attention Mechanism',
    question: 'What is multi-head attention?',
    options: ['Multiple attention layers', 'Attention computed in parallel with different learned projections', 'Attention to multiple inputs', 'Multiple attention functions'],
    correctAnswer: 1
  },
  {
    id: 23,
    topic: 'Model Evaluation',
    question: 'What is perplexity in language models?',
    options: ['Model complexity', 'Uncertainty measure of model predictions', 'Training time', 'Model size'],
    correctAnswer: 1
  },
  {
    id: 24,
    topic: 'AI Ethics',
    question: 'What is a major concern with large language models?',
    options: ['High computational cost', 'Potential for bias and misinformation', 'Slow inference speed', 'Complex architecture'],
    correctAnswer: 1
  },
  {
    id: 25,
    topic: 'RAG',
    question: 'What is the typical workflow of a RAG system?',
    options: ['Retrieve, Augment, Generate', 'Read, Analyze, Generate', 'Retrieve, Analyze, Generate', 'Retrieve, Augment, Evaluate'],
    correctAnswer: 0
  }
];

