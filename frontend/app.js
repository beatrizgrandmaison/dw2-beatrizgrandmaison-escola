const API = "http://localhost:8000"

async function fetchTurmas(){
  try {
    const res = await fetch(`${API}/turmas`)
    if (!res.ok) throw new Error('Erro ao carregar turmas')
    return res.json()
  } catch (error) {
    alert('Erro ao carregar turmas: ' + error.message)
    return []
  }
}

async function fetchAlunos(params={}){
  try {
    const url = new URL(`${API}/alunos`)
    Object.keys(params).forEach(k=>{ if(params[k]) url.searchParams.set(k, params[k]) })
    const res = await fetch(url)
    if (!res.ok) throw new Error('Erro ao carregar alunos')
    return res.json()
  } catch (error) {
    alert('Erro ao carregar alunos: ' + error.message)
    return []
  }
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

let currentSortColumn = 'nome'
let currentSortDirection = 'asc'

function showLoading(show) {
  document.body.style.cursor = show ? 'wait' : 'default'
}

async function renderTable(params={}){
  showLoading(true)
  const tbody = document.querySelector('#alunosTable tbody')
  tbody.innerHTML = ''
  const alunos = await fetchAlunos(params)
  
  // Ordenação
  alunos.sort((a,b)=>{
    let valA = currentSortColumn === 'idade' ? ageFromDob(a.data_nascimento) : a[currentSortColumn]
    let valB = currentSortColumn === 'idade' ? ageFromDob(b.data_nascimento) : b[currentSortColumn]
    const direction = currentSortDirection === 'asc' ? 1 : -1
    return valA > valB ? direction : -direction
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
  showLoading(false)
}

// events
document.addEventListener('DOMContentLoaded', async ()=>{
  await fillTurmaSelects()
  await renderTable()
  await updateIndicators()

  // Filtro por turma
  document.getElementById('filterTurma').addEventListener('change', async (e)=>{
    const turma_id = e.target.value
    await renderTable({
      turma_id,
      status: document.getElementById('filterStatus').value,
      search: document.getElementById('search').value
    })
  })

  // Filtro por status
  document.getElementById('filterStatus').addEventListener('change', async (e)=>{
    const status = e.target.value
    await renderTable({
      status,
      turma_id: document.getElementById('filterTurma').value,
      search: document.getElementById('search').value
    })
  })

  // Busca por nome
  let searchTimeout
  document.getElementById('search').addEventListener('input', async (e)=>{
    clearTimeout(searchTimeout)
    searchTimeout = setTimeout(async () => {
      const search = e.target.value
      await renderTable({
        search,
        status: document.getElementById('filterStatus').value,
        turma_id: document.getElementById('filterTurma').value
      })
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
    
    // Remove sorting indicators from all headers
    document.querySelectorAll('#alunosTable th').forEach(th => {
      th.classList.remove('sort-asc', 'sort-desc')
    })
    
    // Add sorting indicator to current header
    th.classList.add(`sort-${currentSortDirection}`)
    
    await renderTable({
      status: document.getElementById('filterStatus').value,
      turma_id: document.getElementById('filterTurma').value,
      search: document.getElementById('search').value
    })
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

  // Modal de matrícula
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
        if (!turma_id) {
          alert('Selecione uma turma')
          return
        }
        
        showLoading(true)
        try {
          const res = await fetch(`${API}/matriculas`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({aluno_id: Number(id), turma_id: Number(turma_id)})
          })
          if (!res.ok) {
            const err = await res.json()
            throw new Error(err.detail || 'Erro ao matricular aluno')
          }
          matriculaModal.hidden = true
          await renderTable()
          await updateIndicators()
        } catch (error) {
          alert(error.message)
        } finally {
          showLoading(false)
        }
      }
      
      const confirmar = matriculaModal.querySelector('#btnConfirmarMatricula')
      const cancelar = matriculaModal.querySelector('#btnCancelarMatricula')
      
      confirmar.onclick = handleMatricula
      cancelar.onclick = () => { matriculaModal.hidden = true }
    }
  })
})
