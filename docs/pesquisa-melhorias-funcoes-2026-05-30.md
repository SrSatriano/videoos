# Pesquisa de melhorias e funcoes para o Video OS

Data: 2026-05-30

## Fontes oficiais consultadas

- Kdenlive Manual: project bin, timeline, monitors, filters, subtitles, exportacao e workflow.
  https://docs.kdenlive.org/en/
- Kdenlive Media Jobs: automatic scene split, stabilize, proxy clips e clip properties.
  https://docs.kdenlive.org/en/user_interface/menu/media_menu.html
- Shotcut Features: proxy editing, markers/ranges, smart bins, subtitles, scopes, batch export, integrity check e bitrate graph.
  https://shotcut.org/features/
- LosslessCut: cortes/segmentos, scene detection e fluxo rapido baseado em FFmpeg.
  https://github.com/mifi/lossless-cut
- TikTok Business Specs: 9:16 recomendado, minimo 540x960, limite 500 MB e bitrate minimo para ads.
  https://ads.tiktok.com/help/article/tiktok-auction-in-feed-ads
- TikTok Video Ads Specifications: specs oficiais atualizadas para videos verticais e arquivos de safe zone.
  https://ads.tiktok.com/help/article/video-ads-specifications
- YouTube Help: Shorts verticais ou quadrados ate 3 minutos.
  https://support.google.com/youtube/answer/15424877
- Instagram Help: Reels entre 1.91:1 e 9:16, minimo 30 FPS e resolucao minima de 720px.
  https://www.facebook.com/help/instagram/1038071743007909
- Meta for Business Reels Ads: 9:16 com audio e mensagens principais dentro da safe zone.
  https://www.facebook.com/business/ads/facebook-instagram-reels-ads

## Funcoes priorizadas

1. Quality Check por plataforma.
   Validar formato, resolucao, duracao, tamanho, bitrate e avisos de safe area antes de publicar.

2. Smart bins.
   Agrupar automaticamente assets por vertical/horizontal, duracao, importacao, status de proxy, com busca e tags.

3. Waveform e loudness.
   Gerar mini waveform e alerta de audio baixo/alto antes do render.

4. Export analyzer.
   Exibir bitrate, tamanho estimado e recomendacao de CRF antes de criar lote.

5. Scene-to-clips.
   Transformar marcadores de cena em candidatos de corte e lotes automaticamente.

6. Timeline de captions.
   Editar segmentos SRT/VTT visualmente, detectar sobreposicao e palavras viciadas.

7. Safe-zone overlay.
   Preview visual por Instagram/TikTok/Shorts para evitar texto coberto por UI da plataforma.

8. Integrity check.
   Verificar se arquivo esta corrompido, sem audio, sem video ou com metadata incompleta.

9. Preset search/command palette.
   Buscar acoes do app rapidamente, inspirado em editores com busca de comandos.

10. Notes por projeto.
    Guardar roteiro, observacoes, pendencias e checklist por lote/canal.

## Implementado nesta rodada

- Quality Check de renders na tela de Revisao.
- API `POST /api/quality/renders/{id}`.
- Relatorio para Instagram Reels, TikTok e YouTube Shorts.
- Testes automatizados cobrindo render vertical valido e render invalido para Shorts.
- Agentes de pesquisa paralelos para editor features, plataformas sociais e analise do codigo atual.
- Smart Bins automaticos na Biblioteca: todos, prontos para shorts, verticais, ate 60s, longos, com proxy e atencao.
- Selecao em lote pelo bin ativo para acelerar criacao de lotes.
- Safe Zone Studio na Review Bay com overlay visual para Universal, Instagram Reels, TikTok e YouTube Shorts.
- QC agora retorna guias de safe zone por plataforma e guia universal conservador.
- Lista compacta de issues por plataforma dentro do relatorio de qualidade.

## Recomendacoes dos agentes

- Proxima funcao estrutural: Pacote de publicacao 2.0 com titulo, descricao, hashtags, capa, checklist e status por canal.
- Proxima funcao de operacao: gerenciador local de contas/canais com nicho, voz, CTA, hashtags e pasta de saida.
- Proxima funcao visual: editor de posicao de texto/CTA/marca com alerta quando algum elemento sair da safe zone.
