# Histórico de versões

## 1.0.0 — 2026-09-07

- Controle de entregas, histórico, filtros, CSV e ações conforme o status.
- Cadastro de entregadores, seleção de entregas e roteiro apenas de pendentes.
- Numeração por data, sem apagar o histórico na virada do dia.
- Ficha A6 e roteiro A4 compactos em retrato.
- Tema Clinical Tech, fontes locais e telefones com máscara e limite de 15 caracteres.
- Consulta offline PWA em contextos seguros.
- Instalador Windows x64 com Waitress/NSSM, conta LocalService, firewall local e logs.
- Backup SQLite diário, verificação de integridade, retenção e restauração sem sobrescrita.
- Configuração privada e banco separados do código; distribuição sem ferramentas de desenvolvimento.

O registro do serviço e da tarefa requer execução do instalador como Administrador no servidor de destino. HTTPS com certificado confiável é necessário para instalar a PWA em dispositivos remotos; proxy e certificado não são incluídos no instalador.
