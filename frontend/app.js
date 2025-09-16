const API = "http://localhost:8000"

// Simple toast notifications
function showToast(message, type='success', timeout=3500){
  const container = document.getElementById('toastContainer')
  if(!container) return alert(message)
  const t = document.createElement('div')
  t.className = `toast ${type}`
  t.textContent = message
  container.appendChild(t)
  setTimeout(()=>{ t.remove() }, timeout)
}

function showError(message){ showToast(message, 'error', 5000) }

async function fetchTurmas(){
  try {
    const res = await fetch(`${API}/turmas`)
    if (!res.ok) throw new Error('Erro ao carregar turmas')
    return res.json()
  } catch (error) {
    showError('Erro ao carregar turmas: ' + error.message)
    return []
  }
}

async function fetchAlunos(params={}){
  try {
    const url = new URL(`${API}/alunos`)
    Object.keys(params).forEach(k=>{ if(params[k] !== undefined && params[k] !== null && params[k] !== '') url.searchParams.set(k, params[k]) })
    const res = await fetch(url)
    if (!res.ok) throw new Error('Erro ao carregar alunos')
    return res.json()
  } catch (error) {
    showError('Erro ao carregar alunos: ' + error.message)
    return { results: [], total:0 }
  }
}

function ageFromDob(dobStr){
  const dob = new Date(dobStr)
  const diff = Date.now() - dob.getTime()
  return Math.floor(diff/31557600000)
}

let currentSortColumn = localStorage.getItem('sortCol') || 'nome'
let currentSortDirection = localStorage.getItem('sortDir') || 'asc'
let currentPage = 1
const perPage = 10
let totalPagesGlobal = 1

function saveSort(){
  localStorage.setItem('sortCol', currentSortColumn)
  localStorage.setItem('sortDir', currentSortDirection)
}

// update indicators using backend totals (requests with per_page=1 return total)
async function updateIndicators(){
  try{
    const totalData = await fetchAlunos({per_page:1, page:1})
    const total = totalData.total ?? (totalData.results? totalData.results.length : 0)
    const ativosData = await fetchAlunos({per_page:1, page:1, status:'ativo'})
    const ativos = ativosData.total ?? 0
    document.getElementById('indicators').textContent = `Total: ${total} — Ativos: ${ativos}`
  }catch(err){ console.warn('updateIndicators:', err); document.getElementById('indicators').textContent = '' }
}

function showLoading(show) {
  document.body.style.cursor = show ? 'wait' : 'default'
}

async function renderTable(params={}){
  showLoading(true)
  const tbody = document.querySelector('#alunosTable tbody')
  tbody.innerHTML = ''
  params.page = currentPage
  params.per_page = perPage
  const data = await fetchAlunos(params)
  const alunos = data.results || data

  // Ordenação cliente (aplica-se sobre o conjunto retornado)
  alunos.sort((a,b)=>{
    let valA = currentSortColumn === 'idade' ? ageFromDob(a.data_nascimento) : (a[currentSortColumn] ?? '')
    let valB = currentSortColumn === 'idade' ? ageFromDob(b.data_nascimento) : (b[currentSortColumn] ?? '')
    const direction = currentSortDirection === 'asc' ? 1 : -1
    if(valA > valB) return direction
    if(valA < valB) return -direction
    return 0
  })

  alunos.forEach(a=>{
    const tr = document.createElement('tr')
    tr.innerHTML = `
      <td>${a.nome}</td>
      <td>${ageFromDob(a.data_nascimento)}</td>
      <td>${a.turma? a.turma.nome : ''}</td>
      <td>${a.status}</td>
      <td>
        <button data-id="${a.id}" class="btnMat">Matricular</button>
      </td>`
    tbody.appendChild(tr)
  })

  // update pagination info
  const total = data.total ?? alunos.length
  const pageInfo = document.getElementById('pageInfo')
  const totalPages = Math.max(1, Math.ceil(total / perPage))
  totalPagesGlobal = totalPages
  pageInfo.textContent = `Página ${currentPage} de ${totalPages}`

  showLoading(false)
}

// helper to get token if available
function getToken(){ return localStorage.getItem('token') }

async function download(url, filename){
  const res = await fetch(url, {headers: getToken() ? {'Authorization': 'Bearer ' + getToken()} : {}})
  if(!res.ok) { const err = await res.json().catch(()=>({detail:'Erro'})); throw new Error(err.detail || 'Erro ao baixar') }
  const blob = await res.blob()
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
}

// Turma CRUD helpers
async function createTurma(payload){
  const headers = {'Content-Type':'application/json'}
  const token = getToken(); if(token) headers['Authorization'] = 'Bearer ' + token
  const res = await fetch(`${API}/turmas`, {method:'POST', headers, body: JSON.stringify(payload)})
  if(!res.ok) throw await res.json()
  return res.json()
}

async function updateTurma(id, payload){
  const headers = {'Content-Type':'application/json'}
  const token = getToken(); if(token) headers['Authorization'] = 'Bearer ' + token
  const res = await fetch(`${API}/turmas/${id}`, {method:'PUT', headers, body: JSON.stringify(payload)})
  if(!res.ok) throw await res.json()
  return res.json()
}

async function deleteTurma(id){
  const headers = {}
  const token = getToken(); if(token) headers['Authorization'] = 'Bearer ' + token
  const res = await fetch(`${API}/turmas/${id}`, {method:'DELETE', headers})
  if(!res.ok) throw await res.json()
  return true
}

async function fillTurmaSelects(){
  const turmas = await fetchTurmas()
  const filter = document.getElementById('filterTurma')
  const modalSelect = document.querySelector('select[name=turma_id]')
  filter.innerHTML = '<option value="">Todas</option>'
  modalSelect.innerHTML = '<option value="">Nenhuma</option>'
  turmas.forEach(t=>{
    const o = document.createElement('option'); o.value = t.id; o.textContent = `${t.nome} (${t.capacidade})`
    filter.appendChild(o)
    const o2 = o.cloneNode(true)
    modalSelect.appendChild(o2)
  })

  // also fill manage turmas table
  const tbody = document.querySelector('#turmasTable tbody')
  if(tbody){
    tbody.innerHTML = ''
    turmas.forEach(t=>{
      const tr = document.createElement('tr')
      tr.innerHTML = `<td>${t.nome}</td><td>${t.capacidade}</td><td>
        <button data-id="${t.id}" class="editTurma">Editar</button>
        <button data-id="${t.id}" class="delTurma">Deletar</button>
      </td>`
      tbody.appendChild(tr)
    })
  }
}

// client-side email duplicate check
async function emailExists(email){
  const data = await fetchAlunos({per_page: 1000})
  const list = data.results || data
  return list.some(a => a.email && a.email.toLowerCase() === (email||'').toLowerCase())
}

// events
document.addEventListener('DOMContentLoaded', async ()=>{
  await fillTurmaSelects()
  await renderTable()
  await updateIndicators()

  // pagination
  document.getElementById('prevPage').addEventListener('click', async ()=>{ if(currentPage>1){ currentPage--; await renderTable({ status: document.getElementById('filterStatus').value, turma_id: document.getElementById('filterTurma').value, search: document.getElementById('search').value }) } })
  document.getElementById('nextPage').addEventListener('click', async ()=>{ if(currentPage < totalPagesGlobal){ currentPage++; await renderTable({ status: document.getElementById('filterStatus').value, turma_id: document.getElementById('filterTurma').value, search: document.getElementById('search').value }) } })

  // Filtro por turma
  document.getElementById('filterTurma').addEventListener('change', async (e)=>{
    const val = e.target.value
    localStorage.setItem('filterTurma', val)
    currentPage = 1
    await renderTable({ turma_id: val, status: document.getElementById('filterStatus').value, search: document.getElementById('search').value })
  })

  // Filtro por status
  document.getElementById('filterStatus').addEventListener('change', async (e)=>{
    const val = e.target.value
    localStorage.setItem('filterStatus', val)
    currentPage = 1
    await renderTable({ status: val, turma_id: document.getElementById('filterTurma').value, search: document.getElementById('search').value })
  })

  // Busca por nome
  let searchTimeout
  document.getElementById('search').addEventListener('input', async (e)=>{
    clearTimeout(searchTimeout)
    searchTimeout = setTimeout(async () => {
      currentPage = 1
      const search = e.target.value
      await renderTable({ search, status: document.getElementById('filterStatus').value, turma_id: document.getElementById('filterTurma').value })
    }, 300)
  })

  // Ordenação da tabela
  document.querySelector('#alunosTable thead').addEventListener('click', async (e)=>{
    const th = e.target.closest('th')
    if (!th || !th.dataset.sort) return
    if (currentSortColumn === th.dataset.sort) {
      currentSortDirection = currentSortDirection === 'asc' ? 'desc' : 'asc'
    } else {
      currentSortColumn = th.dataset.sort
      currentSortDirection = 'asc'
    }
    saveSort()
    document.querySelectorAll('#alunosTable th').forEach(th => { th.classList.remove('sort-asc', 'sort-desc') })
    th.classList.add(`sort-${currentSortDirection}`)
    await renderTable({ status: document.getElementById('filterStatus').value, turma_id: document.getElementById('filterTurma').value, search: document.getElementById('search').value })
  })

  // restore filters and sorting from localStorage
  const savedFilterTurma = localStorage.getItem('filterTurma') || ''
  const savedFilterStatus = localStorage.getItem('filterStatus') || ''
  if(savedFilterTurma) document.getElementById('filterTurma').value = savedFilterTurma
  if(savedFilterStatus) document.getElementById('filterStatus').value = savedFilterStatus

  // restore sort indicator on header
  const th = document.querySelector(`#alunosTable th[data-sort="${currentSortColumn}"]`)
  if(th) th.classList.add(`sort-${currentSortDirection}`)

  // Novo aluno modal
  document.getElementById('btnNovo').addEventListener('click', ()=>{ document.getElementById('modal').hidden = false; document.getElementById('modal').querySelector('input[name=nome]').focus() })
  document.getElementById('btnClose').addEventListener('click', ()=>{ document.getElementById('modal').hidden = true })

  document.getElementById('formAluno').addEventListener('submit', async (ev)=>{
    ev.preventDefault()
    const fd = new FormData(ev.target)
    const payload = Object.fromEntries(fd.entries())
    if(payload.turma_id==='') payload.turma_id = null
    // front validation: idade >=5
    const dob = new Date(payload.data_nascimento)
    const min = new Date(); min.setFullYear(min.getFullYear() - 5)
    if(dob > min){ showError('Aluno deve ter ao menos 5 anos'); return }
    payload.status = payload.status || 'inativo'

    // email duplicate check
    if(payload.email){
      const exists = await emailExists(payload.email)
      if(exists){ showError('Email já cadastrado'); return }
    }

    const res = await fetch(`${API}/alunos`, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(payload)})
    if(!res.ok){ const err = await res.json().catch(()=>({detail:'Erro'})); showError(err.detail || 'Erro'); return }
    document.getElementById('modal').hidden = true
    showToast('Aluno criado', 'success')
    await fillTurmaSelects()
    await renderTable()
    await updateIndicators()
  })

  // Turma modal create/edit
  document.getElementById('btnNovaTurma').addEventListener('click', ()=>{
    const m = document.getElementById('turmaModal')
    m.hidden = false; m.querySelector('#turmaModalTitle').textContent = 'Nova Turma'
    const form = m.querySelector('#formTurma'); form.reset(); form.id = null; form.querySelector('input[name=nome]').focus()
  })

  document.getElementById('btnCloseTurma').addEventListener('click', ()=>{ document.getElementById('turmaModal').hidden = true })

  document.getElementById('formTurma').addEventListener('submit', async (ev)=>{
    ev.preventDefault();
    const fd = new FormData(ev.target); const payload = Object.fromEntries(fd.entries())
    if(!payload.nome){ showError('Nome é obrigatório'); return }
    payload.capacidade = Number(payload.capacidade) || 1
    try{
      if(payload.id){ // update
        await updateTurma(payload.id, {nome: payload.nome, capacidade: payload.capacidade})
        showToast('Turma atualizada')
      } else {
        await createTurma({nome: payload.nome, capacidade: payload.capacidade})
        showToast('Turma criada')
      }
      document.getElementById('turmaModal').hidden = true
      await fillTurmaSelects()
    } catch(err){
      showError(err.detail || JSON.stringify(err))
    }
  })

  // Manage turmas panel
  document.getElementById('btnGerenciarTurmas').addEventListener('click', ()=>{
    const p = document.getElementById('manageTurmas'); p.hidden = !p.hidden
  })

  // handle edit/delete buttons in turmas table
  document.querySelector('#turmasTable tbody').addEventListener('click', async (e)=>{
    const id = e.target.dataset.id
    if(e.target.classList.contains('editTurma')){
      const turmas = await fetchTurmas(); const t = turmas.find(x=>String(x.id)===String(id))
      if(!t) return showError('Turma não encontrada')
      const m = document.getElementById('turmaModal'); m.hidden = false; m.querySelector('#turmaModalTitle').textContent = 'Editar Turma'
      const form = m.querySelector('#formTurma'); form.id = t.id; form.querySelector('input[name=id]').value = t.id; form.querySelector('input[name=nome]').value = t.nome; form.querySelector('input[name=capacidade]').value = t.capacidade; form.querySelector('input[name=nome]').focus()
    }
    if(e.target.classList.contains('delTurma')){
      if(!confirm('Confirma exclusão da turma?')) return
      try{ await deleteTurma(id); showToast('Turma removida'); await fillTurmaSelects() } catch(err){ showError(err.detail || JSON.stringify(err)) }
    }
  })

  // export buttons
  document.getElementById('btnExportAlunosCsv').addEventListener('click', async ()=>{ try{ await download(`${API}/export/alunos?format=csv`, 'alunos.csv'); showToast('Download iniciado') }catch(e){ showError(e.message) } })
  document.getElementById('btnExportAlunosJson').addEventListener('click', async ()=>{ try{ await download(`${API}/export/alunos?format=json`, 'alunos.json'); showToast('Download iniciado') }catch(e){ showError(e.message) } })
  document.getElementById('btnExportMatriculasCsv').addEventListener('click', async ()=>{ try{ await download(`${API}/export/matriculas?format=csv`, 'matriculas.csv'); showToast('Download iniciado') }catch(e){ showError(e.message) } })
  document.getElementById('btnExportMatriculasJson').addEventListener('click', async ()=>{ try{ await download(`${API}/export/matriculas?format=json`, 'matriculas.json'); showToast('Download iniciado') }catch(e){ showError(e.message) } })

  // handle matricula modal and actions (kept similar to original but using toasts/errors)
  let matriculaModal
  function createMatriculaModal() {
    const modal = document.createElement('div')
    modal.className = 'modal'
    modal.innerHTML = `
      <div class="modal-content">
        <h2>Matricular Aluno</h2>
        <label>Turma
          <select id="matriculaTurma">
            <option value="">Selecione uma turma</option>
          </select>
        </label>
        <div class="modal-actions">
          <button type="button" id="btnConfirmarMatricula">Confirmar</button>
          <button type="button" id="btnCancelarMatricula">Cancelar</button>
        </div>
      </div>`
    document.body.appendChild(modal)
    return modal
  }

  document.querySelector('#alunosTable').addEventListener('click', async (e)=>{
    if(e.target.classList.contains('btnMat')){
      const id = e.target.dataset.id
      if (!matriculaModal) {
        matriculaModal = createMatriculaModal()
        const select = matriculaModal.querySelector('#matriculaTurma')
        const turmas = await fetchTurmas()
        turmas.forEach(t => {
          const o = document.createElement('option')
          o.value = t.id
          o.textContent = `${t.nome} (${t.capacidade})`
          select.appendChild(o)
        })
      }
      matriculaModal.hidden = false
      const handleMatricula = async () => {
        const turma_id = matriculaModal.querySelector('#matriculaTurma').value
        if (!turma_id) { showError('Selecione uma turma'); return }
        showLoading(true)
        try {
          const res = await fetch(`${API}/matriculas`, { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({aluno_id: Number(id), turma_id: Number(turma_id)}) })
          if (!res.ok) { const err = await res.json().catch(()=>({detail:'Erro'})); throw new Error(err.detail || 'Erro ao matricular aluno') }
          matriculaModal.hidden = true
          showToast('Matrícula efetuada')
          await renderTable()
          await updateIndicators()
        } catch (error) { showError(error.message) } finally { showLoading(false) }
      }
      const confirmar = matriculaModal.querySelector('#btnConfirmarMatricula')
      const cancelar = matriculaModal.querySelector('#btnCancelarMatricula')
      confirmar.onclick = handleMatricula
      cancelar.onclick = () => { matriculaModal.hidden = true }
    }
  })
})
