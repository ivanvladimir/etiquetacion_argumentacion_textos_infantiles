from pathlib import Path

def sanitize_filename(filename: str) -> str:
    # Remove/replace invalid characters
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    
    # Remove leading/trailing spaces and dots
    filename = filename.strip('. ')
    
    # Limit length (255 is typical filesystem limit)
    filename = filename[:255]
    
    return filename

def postprocess_token_classification(predictions, tokens, id2label):
    """
    Creates HTML tags for entities with the same label.
    Outside labels (O) are left as plain text.
    """
    results = []
    current_word = ""
    current_label = None
    start_idx = 0
    
    for idx, (token, pred_id) in enumerate(zip(tokens, predictions)):
        label = id2label[pred_id]
        
        # Skip special tokens
        if token in ['[CLS]', '[SEP]', '[PAD]', "<s>", "</s>"]:
            continue
        
        # Handle subword tokens (starting with ▁)
        if token.startswith('▁'):
            # Save previous word if exists
            if current_word:
                results.append({
                    'text': current_word,
                    'label': current_label,
                })
            current_word = token[1:]
            current_label = label.split('-',1)[1]
            start_idx = idx
        else:
            current_word += token
    
    # Don't forget the last word
    if current_word:
        results.append({
            'text': current_word,
            'label': current_label,
        })
    
    return results

def merge_contiguous_labels(spans):
    """
    Merges contiguous spans with the same label into one span.
    """
    if not spans:
        return []
    
    merged = []
    current_span = spans[0].copy()
    
    for i in range(1, len(spans)):
        next_span = spans[i]
        
        # If labels are the same and not 'O', merge them
        if current_span['label'] == next_span['label']:
            # Merge the spans
            current_span['text'] += ' ' + next_span['text']
        else:
            # Different label or 'O', save current and start new
            merged.append(current_span)
            current_span = next_span.copy()
    
    # Don't forget the last span
    merged.append(current_span)
    
    return merged


def create_html_output(spans):
    """
    Converts spans to HTML with tags for entities.
    Labels marked as 'O' (outside) are left as plain text.
    Same consecutive labels are grouped together in one tag.
    """
    # Merge contiguous labels first
    merged_spans = merge_contiguous_labels(spans)

    html_parts = []
    
    for span in merged_spans:
        text = span['text']
        label = span['label']
        
        # If label is 'O', add as plain text
        if label == 'O' or label is None:
            html_parts.append(text)
        else:
            # Create HTML tag with label
            # Convert label to valid CSS class name (remove special chars)
            class_name = label.replace('-', '_').lower()
            html_parts.append(f'<span class="labeled-span" label_type="{class_name}">{text}</span>')
    
    # Join with spaces
    html_output = ' '.join(html_parts)
    return html_output
