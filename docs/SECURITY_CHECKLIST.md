# Security Checklist - Terceros

Usar antes de integrar cualquier repo/componente de comunidad.

- Licencia compatible revisada.
- Pin por tag o commit hash.
- Comandos ejecutados por instalación identificados.
- Accesos a filesystem revisados.
- Llamadas de red identificadas.
- Permisos peligrosos evaluados.
- Secrets handling validado (sin hardcode).
- Registro en `docs/INTEGRATIONS.md` completado.
- ADR creada si hay decisiones de riesgo o parches locales.
