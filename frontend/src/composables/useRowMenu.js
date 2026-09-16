import { ref, onMounted, onBeforeUnmount } from 'vue'

// Menu de ações das linhas de tabela. O painel usa position: fixed para
// não ser cortado pelo overflow-x da tabela; as coordenadas vêm do botão.
export function useRowMenu() {
  const openMenu = ref(null)
  const menuPos = ref({ top: 0, left: 0 })
  let lastOpenedAt = 0

  function toggleMenu(id) {
    if (openMenu.value === id) {
      openMenu.value = null
      return
    }
    const button = document.querySelector(`[data-menu="${id}"]`)
    if (button) {
      const rect = button.getBoundingClientRect()
      const width = 200
      const left = Math.max(8, Math.min(window.innerWidth - width - 8, rect.right))
      menuPos.value = { top: rect.bottom + 6, left }
    }
    lastOpenedAt = Date.now()
    openMenu.value = id
  }

  function closeMenus() {
    openMenu.value = null
  }

  // O clique no botão pode rolar a página (foco) e disparar scroll no mesmo
  // instante; ignora scrolls logo após abrir e só fecha em rolagens reais.
  function onScroll() {
    if (openMenu.value && Date.now() - lastOpenedAt > 300) {
      openMenu.value = null
    }
  }

  onMounted(() => {
    document.addEventListener('click', closeMenus)
    window.addEventListener('scroll', onScroll, true)
  })

  onBeforeUnmount(() => {
    document.removeEventListener('click', closeMenus)
    window.removeEventListener('scroll', onScroll, true)
  })

  return { openMenu, menuPos, toggleMenu, closeMenus }
}
