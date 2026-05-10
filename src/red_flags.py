from __future__ import annotations

# Lista canonica deduplicada para a rodada principal.
#
# A metodologia do estudo base primeiro identifica caracteristicas em uma amostra
# pequena, remove atributos repetidos e congela o conjunto usado na avaliacao.
# Por isso, sinais semanticamente equivalentes ficam mapeados em aliases abaixo,
# em vez de virarem colunas separadas.
RED_FLAGS: list[str] = [
    "remetente_suspeito",
    "senso_urgencia_medo",
    "solicitacao_dados_sensiveis",
    "links_suspeitos",
    "erros_gramaticais",
    "email_nao_solicitado",
    "saudacao_generica",
    "anexos_suspeitos",
    "formatacao_estranha",
    "oferta_boa_demais",
    "dominio_suspeito",
    "historias_elaboradas",
    "personalizacao_excessiva",
    "contato_ausente_ou_inconsistente",
    "conteudo_emocional",
    "endereco_resposta_diferente",
    "botoes_enganosos",
]


RED_FLAG_DEFINITIONS: dict[str, str] = {
    "remetente_suspeito": "Remetente desconhecido, dominio estranho, endereco forjado ou identidade inconsistente.",
    "senso_urgencia_medo": "Pressao para acao imediata, ameaca, bloqueio, expiracao ou medo.",
    "solicitacao_dados_sensiveis": "Pedido de senha, credenciais, dados bancarios, documentos ou informacoes pessoais.",
    "links_suspeitos": "Links encurtados, mascarados, externos, com dominio estranho ou chamada para login suspeito.",
    "erros_gramaticais": "Erros gramaticais, ortograficos, traducao ruim ou linguagem pouco profissional.",
    "email_nao_solicitado": "Mensagem inesperada ou sem relacao clara com uma acao previa do destinatario.",
    "saudacao_generica": "Saudacao generica ou falta de personalizacao basica esperada.",
    "anexos_suspeitos": "Anexos executaveis, compactados, com macros, nomes genericos ou fora de contexto.",
    "formatacao_estranha": "Formatacao visual inconsistente, HTML suspeito, excesso de destaque ou baixa qualidade.",
    "oferta_boa_demais": "Promessa improvavel de premio, dinheiro, recompensa ou beneficio excessivo.",
    "dominio_suspeito": "Dominio que imita marca legitima, usa TLD estranho ou nao corresponde ao remetente alegado.",
    "historias_elaboradas": "Narrativa longa, improvavel ou manipulativa para convencer o destinatario.",
    "personalizacao_excessiva": "Uso de dados pessoais para criar falsa legitimidade alem do esperado.",
    "contato_ausente_ou_inconsistente": "Contato ausente, divergente ou incompativel com a organizacao alegada.",
    "conteudo_emocional": "Apelo emocional forte, pena, medo, empatia ou ameaca sem necessidade operacional clara.",
    "endereco_resposta_diferente": "Reply-To ou endereco de resposta diferente do remetente principal.",
    "botoes_enganosos": "Botoes ou chamadas visuais que escondem destino real ou induzem clique.",
}


RED_FLAG_ALIASES: dict[str, str] = {
    "remetente_falsificado": "remetente_suspeito",
    "sender_spoofing": "remetente_suspeito",
    "anexos_estranhos": "anexos_suspeitos",
    "anexos_com_nomes_estranhos": "anexos_suspeitos",
    "falta_contato": "contato_ausente_ou_inconsistente",
    "inconsistencias_contato": "contato_ausente_ou_inconsistente",
    "falta_de_informacao_de_contato": "contato_ausente_ou_inconsistente",
    "informacoes_de_contato_inconsistentes": "contato_ausente_ou_inconsistente",
    "falta_personalizacao": "saudacao_generica",
    "falta_de_personalizacao": "saudacao_generica",
}
