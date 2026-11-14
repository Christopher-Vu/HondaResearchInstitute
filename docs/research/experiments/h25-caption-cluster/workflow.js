export const meta = {
  name: 'h25-caption-cluster',
  description: 'H25: caption each failing route from its last camera frames, then group the captions into failure modes',
  phases: [
    { title: 'Caption', detail: 'one agent per failing route reads 4 frames and explains the failure' },
    { title: 'Group', detail: 'independent runs per pool build a taxonomy and assign every route' },
  ],
}

// args: {pools: [{name, frames_dir, ids: [{id, frames}]}], runs: 6}. Pool names are neutral (a, b). Agents see opaque
// ids and frames only; the mapping to route ids lives outside frames_dir. ids are sorted here, so their order cannot
// carry route ids or categories whatever order the caller passes.

const CAPTION = {
  type: 'object',
  properties: {
    scene: { type: 'string', description: 'what is in front of the car that matters, in one or two sentences' },
    reason: { type: 'string', description: 'the most likely reason the driving AI failed, in one or two sentences' },
    mode: { type: 'string', description: 'a short phrase naming the kind of failure, 3 to 8 words' },
  },
  required: ['scene', 'reason', 'mode'],
}

const GROUPS = {
  type: 'object',
  properties: {
    modes: {
      type: 'array',
      maxItems: 10,
      items: {
        type: 'object',
        properties: { name: { type: 'string' }, members: { type: 'array', items: { type: 'string' } } },
        required: ['name', 'members'],
      },
    },
  },
  required: ['modes'],
}

function captionPrompt(dir, item) {
  const files = Array.from({ length: item.frames }, (_, i) => `${dir}/${item.id}/f${i}.png`)
  return `You are looking at ${item.frames} frame(s) from the forward camera of a car driven by an AI in a driving simulator.
The frames are one second apart, oldest first: ${files.join(', ')}.
Read each of these images with the Read tool. Do not open, list or search any other file or folder.
The episode ended in a failure, such as a collision, getting stuck, leaving the lane or a traffic violation, at or
shortly after the last frame. Look at what is in the scene and how it changes across the frames, think step by step
about what the AI most likely did wrong, then answer. Describe only what you can see; if the frames do not show the
cause, say so in the reason.`
}

const flat = text => String(text).replace(/\s+/g, ' ').trim()

function groupPrompt(items) {
  const lines = items.map(item => `${item.id}: scene: ${flat(item.scene)} | reason: ${flat(item.reason)} | mode: ${flat(item.mode)}`)
  return `Below are descriptions of ${items.length} failed episodes of a driving AI in a simulator, one per line,
each starting with its id. First decide on a taxonomy of at most 10 failure modes that explains these failures,
grouping by the cause of the failure. Then assign every id to exactly one mode. Use every id exactly once and copy
ids exactly. Name each mode in a few plain words. Do not use any tool: everything you need is below.

${lines.join('\n')}`
}

function order(items, run) {
  const k = items.length
  const step = [1, 7, 11, 13, 17, 19][run % 6]
  const usable = k % step === 0 ? 1 : step
  return items.map((_, i) => items[(i * usable + run) % k])
}

const runs = args.runs ?? 6
const results = {}
for (const pool of args.pools) {
  const items = [...pool.ids].sort((a, b) => (a.id < b.id ? -1 : a.id > b.id ? 1 : 0))
  phase('Caption')
  const captions = (await parallel(items.map(item => () =>
    agent(captionPrompt(pool.frames_dir, item), { label: `caption:${pool.name}`, phase: 'Caption', schema: CAPTION })
      .then(c => (c ? { id: item.id, ...c } : null))))).filter(Boolean)
  log(`${pool.name}: ${captions.length} of ${items.length} routes captioned`)
  phase('Group')
  const grouped = await parallel(Array.from({ length: runs }, (_, run) => () =>
    agent(groupPrompt(order(captions, run)), { label: `group:${pool.name}:${run}`, phase: 'Group', schema: GROUPS })
      .then(g => ({ run, modes: g ? g.modes : [], failed: !g }))))
  const known = new Set(captions.map(c => c.id))
  const checked = grouped.map(g => {
    const placed = new Set()
    let invented = 0, duplicated = 0
    const modes = g.modes.map(m => {
      const members = []
      for (const id of m.members) {
        if (!known.has(id)) { invented++; continue }
        if (placed.has(id)) { duplicated++; continue }
        placed.add(id); members.push(id)
      }
      return { name: flat(m.name), members }
    })
    const unassigned = [...known].filter(id => !placed.has(id)).length
    if (invented || duplicated || unassigned || g.failed) log(`${pool.name} run ${g.run}: ${invented} unknown ids dropped, ${duplicated} repeats dropped, ${unassigned} unassigned${g.failed ? ', agent failed (scored as no axes)' : ''}`)
    return { run: g.run, modes, invented, duplicated, unassigned, failed: g.failed }
  })
  results[pool.name] = { captions, runs: checked }
}
return results
