/**
 * Generic Agent Response Renderer — ExcellStudy
 * Safely parses and displays the agent's content blocks with element escaping.
 */

const OUTPUT_RENDERERS = {
  verdict: renderVerdictCard,
  annotated_image: renderAnnotatedImage,
  score: renderScoreCard,
  diff: renderDiffCard,
  text: renderTextBlock,
  step_list: renderStepList,
  comparison: renderComparisonTable,
  hint: renderHintPanel,
};

function renderAgentResponse(contentBlocks) {
  const container = document.getElementById("agent-response");
  container.innerHTML = "";

  if (!Array.isArray(contentBlocks) || contentBlocks.length === 0) {
    container.appendChild(renderTextBlock({ value: "No response received." }));
    return;
  }

  // Pre-sort hints by reveal_order if present
  const hints = [];
  const otherBlocks = [];

  contentBlocks.forEach((block) => {
    if (block.type === 'hint') {
      hints.push(block);
    } else {
      otherBlocks.push(block);
    }
  });

  hints.sort((a, b) => {
    const orderA = a.reveal_order !== undefined ? a.reveal_order : 999;
    const orderB = b.reveal_order !== undefined ? b.reveal_order : 999;
    return orderA - orderB;
  });

  // Render non-hint blocks first, then hints at the bottom
  const sortedBlocks = [...otherBlocks, ...hints];

  sortedBlocks.forEach((block) => {
    const renderer = OUTPUT_RENDERERS[block.type];
    if (!renderer) {
      console.warn(`Unknown content block type: ${block.type}`);
      return;
    }
    try {
      container.appendChild(renderer(block));
    } catch (e) {
      console.error(`Error rendering block type ${block.type}:`, e);
    }
  });
}

function renderVerdictCard(block) {
  const card = document.createElement('div');
  card.className = 'response-card flex items-start gap-3 border-l-4 ' + 
                   (block.correct ? 'border-l-[#1D9E75] bg-[#1D9E75]/5' : 'border-l-[#E05252] bg-[#E05252]/5');

  const icon = document.createElement('div');
  icon.className = 'w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0 text-white font-bold text-xs ' + 
                  (block.correct ? 'bg-[#1D9E75]' : 'bg-[#E05252]');
  icon.textContent = block.correct ? '✓' : '✕';

  const body = document.createElement('div');
  body.className = 'flex-1 min-w-0';

  const title = document.createElement('h3');
  title.className = 'font-bold text-sm text-[#1A1A2E]';
  title.textContent = block.correct ? 'Correct Answer' : 'Incorrect Answer';

  const summaryText = document.createElement('p');
  summaryText.className = 'text-xs text-[#6B7280] mt-1 leading-relaxed';
  summaryText.textContent = block.summary || '';

  body.appendChild(title);
  body.appendChild(summaryText);

  if (block.confidence !== undefined && block.confidence !== null) {
    const confidenceVal = parseFloat(block.confidence);
    const confidenceLabel = document.createElement('span');
    confidenceLabel.className = 'text-[10px] text-[#6B7280] font-medium block mt-2';
    confidenceLabel.textContent = `Confidence: ${Math.round(confidenceVal * 100)}%`;

    const progressBg = document.createElement('div');
    progressBg.className = 'w-full h-1 bg-gray-200 rounded-full mt-1 overflow-hidden';

    const progressFill = document.createElement('div');
    progressFill.className = 'h-full ' + (block.correct ? 'bg-[#1D9E75]' : 'bg-[#E05252]');
    progressFill.style.width = `${Math.min(Math.max(confidenceVal * 100, 0), 100)}%`;

    progressBg.appendChild(progressFill);
    body.appendChild(confidenceLabel);
    body.appendChild(progressBg);
  }

  card.appendChild(icon);
  card.appendChild(body);
  return card;
}

function renderAnnotatedImage(block) {
  const card = document.createElement('div');
  card.className = 'response-card space-y-3';

  const wrapper = document.createElement('div');
  wrapper.className = 'relative inline-block w-full overflow-hidden rounded-lg border border-[#E5E4F0]';

  const img = document.createElement('img');
  img.src = block.image_url || block.value || '';
  img.className = 'w-full h-auto block';
  wrapper.appendChild(img);

  if (Array.isArray(block.markup)) {
    block.markup.forEach((pin, idx) => {
      const marker = document.createElement('div');
      marker.className = 'absolute w-6 h-6 rounded-full border border-white flex items-center justify-center text-[10px] font-bold text-white shadow cursor-pointer transition-all transform hover:scale-110 group';

      const isCorrect = pin.status === 'correct';
      marker.style.background = isCorrect ? '#1D9E75' : '#BA7517';
      if (pin.status === 'incorrect') marker.style.background = '#E05252';

      marker.style.left = `${pin.x}%`;
      marker.style.top = `${pin.y}%`;
      marker.style.transform = 'translate(-50%, -50%)';

      marker.textContent = (idx + 1).toString();

      const tooltip = document.createElement('div');
      tooltip.className = 'absolute bottom-full left-1/2 -translate-x-1/2 mb-1.5 hidden group-hover:block bg-[#1A1A2E] text-white text-[10px] py-1 px-2 rounded whitespace-nowrap shadow-lg z-30 font-normal';
      tooltip.textContent = pin.label || '';

      marker.appendChild(tooltip);
      wrapper.appendChild(marker);
    });
  }

  card.appendChild(wrapper);
  return card;
}

function renderScoreCard(block) {
  const card = document.createElement('div');
  card.className = 'response-card flex flex-col items-center p-6 text-center';

  const title = document.createElement('h3');
  title.className = 'text-xs font-semibold text-[#6B7280] uppercase tracking-wider mb-2';
  title.textContent = 'Score';

  const scoreDiv = document.createElement('div');
  scoreDiv.className = 'flex items-baseline gap-1';

  const valSpan = document.createElement('span');
  valSpan.className = 'text-4xl font-extrabold text-[#534AB7]';
  valSpan.textContent = block.value !== undefined ? block.value : '0';

  const slashSpan = document.createElement('span');
  slashSpan.className = 'text-xl text-[#9CA3AF] font-medium';
  slashSpan.textContent = '/';

  const maxSpan = document.createElement('span');
  maxSpan.className = 'text-2xl font-bold text-[#6B7280]';
  maxSpan.textContent = block.max !== undefined ? block.max : '100';

  scoreDiv.appendChild(valSpan);
  scoreDiv.appendChild(slashSpan);
  scoreDiv.appendChild(maxSpan);

  card.appendChild(title);
  card.appendChild(scoreDiv);

  if (block.breakdown && typeof block.breakdown === 'object') {
    const breakdownList = document.createElement('ul');
    breakdownList.className = 'w-full mt-4 border-t border-[#E5E4F0] pt-3 text-left space-y-1.5';

    for (const [key, val] of Object.entries(block.breakdown)) {
      const item = document.createElement('li');
      item.className = 'flex justify-between text-xs text-[#6B7280]';

      const keySpan = document.createElement('span');
      keySpan.textContent = key;

      const valSpan = document.createElement('span');
      valSpan.className = 'font-semibold text-[#1A1A2E]';
      valSpan.textContent = val;

      item.appendChild(keySpan);
      item.appendChild(valSpan);
      breakdownList.appendChild(item);
    }
    card.appendChild(breakdownList);
  }

  return card;
}

function renderDiffCard(block) {
  const card = document.createElement('div');
  card.className = 'response-card space-y-4';

  const grid = document.createElement('div');
  grid.className = 'grid grid-cols-1 md:grid-cols-2 gap-4';

  const leftCol = document.createElement('div');
  leftCol.className = 'p-4 rounded-lg bg-gray-50 border border-[#E5E4F0]';
  const leftTitle = document.createElement('span');
  leftTitle.className = 'text-[10px] font-semibold uppercase tracking-wider text-[#6B7280] block mb-1';
  leftTitle.textContent = "Your Answer";
  const leftVal = document.createElement('p');
  leftVal.className = 'text-sm text-[#6B7280] line-through font-mono whitespace-pre-wrap';
  leftVal.textContent = block.learner_answer || '';
  leftCol.appendChild(leftTitle);
  leftCol.appendChild(leftVal);

  const rightCol = document.createElement('div');
  rightCol.className = 'p-4 rounded-lg bg-[#1D9E75]/5 border border-[#1D9E75]/20';
  const rightTitle = document.createElement('span');
  rightTitle.className = 'text-[10px] font-semibold uppercase tracking-wider text-[#1D9E75] block mb-1';
  rightTitle.textContent = "Correct Answer";
  const rightVal = document.createElement('p');
  rightVal.className = 'text-sm text-[#1D9E75] font-bold font-mono whitespace-pre-wrap';
  rightVal.textContent = block.correct_answer || '';
  rightCol.appendChild(rightTitle);
  rightCol.appendChild(rightVal);

  grid.appendChild(leftCol);
  grid.appendChild(rightCol);
  card.appendChild(grid);

  if (block.explanation) {
    const explanationBox = document.createElement('div');
    explanationBox.className = 'p-3 rounded bg-[#534AB7]/5 text-xs text-[#534AB7] leading-relaxed border border-[#534AB7]/10';
    const expTitle = document.createElement('strong');
    expTitle.className = 'block mb-1';
    expTitle.textContent = 'Explanation:';
    const expText = document.createElement('span');
    expText.textContent = block.explanation;

    explanationBox.appendChild(expTitle);
    explanationBox.appendChild(expText);
    card.appendChild(explanationBox);
  }

  return card;
}

function renderTextBlock(block) {
  const card = document.createElement('div');
  card.className = 'response-card';

  const p = document.createElement('p');
  p.className = 'text-sm text-[#1A1A2E] leading-relaxed whitespace-pre-wrap';
  p.textContent = block.value || '';

  card.appendChild(p);
  return card;
}

function renderStepList(block) {
  const card = document.createElement('div');
  card.className = 'response-card space-y-3';

  if (Array.isArray(block.steps)) {
    const ol = document.createElement('ol');
    ol.className = 'space-y-2';

    block.steps.forEach((stepText, idx) => {
      const li = document.createElement('li');
      li.className = 'p-3 rounded-lg border border-[#E5E4F0] flex gap-3 items-start bg-white';

      const num = document.createElement('span');
      num.className = 'w-6 h-6 rounded-full bg-[#534AB7]/10 text-[#534AB7] text-xs font-bold flex items-center justify-center flex-shrink-0';
      num.textContent = (idx + 1).toString();

      const text = document.createElement('p');
      text.className = 'text-xs text-[#1A1A2E] leading-relaxed mt-0.5';
      text.textContent = stepText;

      li.appendChild(num);
      li.appendChild(text);
      ol.appendChild(li);
    });
    card.appendChild(ol);
  }
  return card;
}

function renderComparisonTable(block) {
  const card = document.createElement('div');
  card.className = 'response-card overflow-x-auto';

  const table = document.createElement('table');
  table.className = 'min-w-full border-collapse text-left text-xs';

  if (Array.isArray(block.headers)) {
    const thead = document.createElement('thead');
    const tr = document.createElement('tr');
    tr.className = 'border-b-2 border-[#E5E4F0] bg-gray-50';

    block.headers.forEach(headerText => {
      const th = document.createElement('th');
      th.className = 'p-3 font-semibold text-[#6B7280] uppercase tracking-wider';
      th.textContent = headerText;
      tr.appendChild(th);
    });
    thead.appendChild(tr);
    table.appendChild(thead);
  }

  if (Array.isArray(block.rows)) {
    const tbody = document.createElement('tbody');
    block.rows.forEach((row, rowIdx) => {
      const tr = document.createElement('tr');
      tr.className = 'border-b border-[#E5E4F0] transition-colors hover:bg-[#F8F7FF] ' + 
                   (rowIdx % 2 === 1 ? 'bg-gray-50/50' : '');

      if (Array.isArray(row)) {
        row.forEach(cellText => {
          const td = document.createElement('td');
          td.className = 'p-3 text-[#1A1A2E] leading-relaxed';
          td.textContent = cellText;
          tr.appendChild(td);
        });
      }
      tbody.appendChild(tr);
    });
    table.appendChild(tbody);
  }

  card.appendChild(table);
  return card;
}

function renderHintPanel(block) {
  const card = document.createElement('div');
  card.className = 'response-card border-l-4 border-l-[#BA7517] bg-[#BA7517]/5 p-0 overflow-hidden';

  const header = document.createElement('button');
  header.className = 'w-full flex items-center justify-between p-4 text-left font-semibold text-[#BA7517]';

  const titleDiv = document.createElement('div');
  titleDiv.className = 'flex items-center gap-2 text-sm';

  const icon = document.createElement('span');
  icon.textContent = '💡';

  const label = document.createElement('span');
  label.textContent = 'Hint';

  titleDiv.appendChild(icon);
  titleDiv.appendChild(label);

  const chevron = document.createElement('span');
  chevron.textContent = '▼';
  chevron.style.fontSize = '0.75rem';
  chevron.style.transition = 'transform 0.2s';

  header.appendChild(titleDiv);
  header.appendChild(chevron);
  card.appendChild(header);

  const body = document.createElement('div');
  body.className = 'max-h-0 overflow-hidden transition-all duration-300 ease-in-out';

  const p = document.createElement('p');
  p.className = 'p-4 pt-0 text-xs text-[#1A1A2E] leading-relaxed';
  p.textContent = block.value || '';
  body.appendChild(p);
  card.appendChild(body);

  header.addEventListener('click', () => {
    const isOpen = body.style.maxHeight && body.style.maxHeight !== '0px';
    if (isOpen) {
      body.style.maxHeight = '0px';
      chevron.style.transform = 'rotate(0deg)';
    } else {
      body.style.maxHeight = `${body.scrollHeight}px`;
      chevron.style.transform = 'rotate(180deg)';
    }
  });

  return card;
}
