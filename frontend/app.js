const API = "http://localhost:8000"

async function fetchTurmas(){
  const res = await fetch(`${API}/turmas`)
  return res.json()
}

async function fetchAlunos(params={}){
  const url = new URL(`${API}/alunos`)
  Object.keys(params).forEach(k=>{ if(params[k]) url.searchParams.set(k, params[k]) })
  const res = await fetch(url)
  return res.json()
}

function ageFromDob(dobStr){
  const dob = new Date(dobStr)
  const diff = Date.now() - dob.getTime()
  return Math.floor(diff/31557600000)
}

async function updateIndicators(){
  const alunos = await fetchAlunos()
  const total = alunos.length
  const ativos = alunos.filter(a=>a.status=="ativo").length
  document.getElementById('indicators').textContent = `Total: ${total} — Ativos: ${ativos}`
}

async function fillTurmaSelects(){
  const turmas = await fetchTurmas()
  const filter = document.getElementById('filterTurma')
  const modalSelect = document.querySelector('select[name=turma_id]')
  turmas.forEach(t=>{
    const o = document.createElement('option'); o.value = t.id; o.textContent = `${t.nome} (${t.capacidade})`
    filter.appendChild(o)
    const o2 = o.cloneNode(true)
    modalSelect.appendChild(o2)
  })
}

async function renderTable(params={}){
  const tbody = document.querySelector('#alunosTable tbody')
  tbody.innerHTML = ''
  const alunos = await fetchAlunos(params)
  alunos.sort((a,b)=>a.nome.localeCompare(b.nome))
  alunos.forEach(a=>{
    const tr = document.createElement('tr')
    tr.innerHTML = `<td>${a.nome}</td><td>${ageFromDob(a.data_nascimento)}</td><td>${a.turma? a.turma.nome : ''}</td><td>${a.status}</td><td><button data-id="${a.id}" class="btnMat">Matricular</button></td>`
    tbody.appendChild(tr)
  })
}

// events
document.addEventListener('DOMContentLoaded', async ()=>{
  await fillTurmaSelects()
  await renderTable()
  await updateIndicators()

  document.getElementById('filterTurma').addEventListener('change', async (e)=>{
    const turma_id = e.target.value
    await renderTable({turma_id})
  })

  document.getElementById('btnNovo').addEventListener('click', ()=>{
    document.getElementById('modal').hidden = false
  })

  document.getElementById('btnClose').addEventListener('click', ()=>{
    document.getElementById('modal').hidden = true
  })

  document.getElementById('formAluno').addEventListener('submit', async (ev)=>{
    ev.preventDefault()
    const fd = new FormData(ev.target)
    const payload = Object.fromEntries(fd.entries())
    if(payload.turma_id==='') payload.turma_id = null
    // front validation: idade >=5
    const dob = new Date(payload.data_nascimento)
    const min = new Date(); min.setFullYear(min.getFullYear() - 5)
    if(dob > min){ alert('Aluno deve ter ao menos 5 anos'); return }
    payload.status = payload.status || 'inativo'
    const res = await fetch(`${API}/alunos`, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(payload)})
    if(!res.ok){ const err = await res.json(); alert(err.detail || 'Erro'); return }
    document.getElementById('modal').hidden = true
    await renderTable()
    await updateIndicators()
  })

  document.querySelector('#alunosTable').addEventListener('click', async (e)=>{
    if(e.target.classList.contains('btnMat')){
      const id = e.target.dataset.id
      const turma_id = prompt('ID da turma para matricular:')
      if(!turma_id) return
      const res = await fetch(`${API}/matriculas`, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({aluno_id: Number(id), turma_id: Number(turma_id)})})
      if(!res.ok){ const err = await res.json(); alert(err.detail || 'Erro'); return }
      await renderTable()
      await updateIndicators()
    }
  })
})
