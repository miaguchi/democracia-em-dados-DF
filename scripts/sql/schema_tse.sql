-- =============================================================================
-- Schema normalizado para dados eleitorais do TSE
-- Fonte: votacao_partido_munzona (1998-2022), Distrito Federal
-- Projeto: Democracia em Dados — replicação DF
-- =============================================================================

-- Dimensão: municípios
CREATE TABLE IF NOT EXISTS municipio (
    cd_municipio    INT          NOT NULL,
    nm_municipio    VARCHAR(100) NOT NULL,
    sg_uf           CHAR(2)      NOT NULL DEFAULT 'DF',
    PRIMARY KEY (cd_municipio)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Dimensão: zonas eleitorais
CREATE TABLE IF NOT EXISTS zona_eleitoral (
    nr_zona         INT          NOT NULL,
    cd_municipio    INT          NOT NULL,
    PRIMARY KEY (nr_zona, cd_municipio),
    FOREIGN KEY (cd_municipio) REFERENCES municipio(cd_municipio)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Dimensão: partidos
CREATE TABLE IF NOT EXISTS partido (
    nr_partido      INT          NOT NULL,
    sg_partido      VARCHAR(20)  NOT NULL,
    nm_partido      VARCHAR(100) NOT NULL,
    PRIMARY KEY (nr_partido)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Dimensão: cargos
CREATE TABLE IF NOT EXISTS cargo (
    cd_cargo        INT          NOT NULL,
    ds_cargo        VARCHAR(50)  NOT NULL,
    PRIMARY KEY (cd_cargo)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Dimensão: eleições
CREATE TABLE IF NOT EXISTS eleicao (
    cd_eleicao      INT          NOT NULL,
    ano_eleicao     SMALLINT     NOT NULL,
    nr_turno        TINYINT      NOT NULL,
    cd_tipo_eleicao INT          NOT NULL,
    nm_tipo_eleicao VARCHAR(50)  NOT NULL,
    ds_eleicao      VARCHAR(100) NOT NULL,
    dt_eleicao      DATE         NOT NULL,
    tp_abrangencia  CHAR(1)      NOT NULL COMMENT 'M=municipal, E=estadual, F=federal',
    PRIMARY KEY (cd_eleicao, nr_turno)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Fato: votação por partido, município e zona
CREATE TABLE IF NOT EXISTS votacao_partido_munzona (
    id              BIGINT       NOT NULL AUTO_INCREMENT,
    cd_eleicao      INT          NOT NULL,
    nr_turno        TINYINT      NOT NULL,
    cd_municipio    INT          NOT NULL,
    nr_zona         INT          NOT NULL,
    cd_cargo        INT          NOT NULL,
    nr_partido      INT          NOT NULL,
    qt_votos_nominais   INT      NOT NULL DEFAULT 0,
    qt_votos_legenda    INT      NOT NULL DEFAULT 0,
    st_voto_em_transito CHAR(1)  NOT NULL DEFAULT 'N',
    -- Coligação / federação (desnormalizado por conveniência — muda a cada eleição)
    sq_coligacao            BIGINT       NULL,
    nm_coligacao            VARCHAR(100) NULL,
    ds_composicao_coligacao VARCHAR(200) NULL,
    tp_agremiacao           VARCHAR(20)  NULL,
    PRIMARY KEY (id),
    FOREIGN KEY (cd_eleicao, nr_turno) REFERENCES eleicao(cd_eleicao, nr_turno),
    FOREIGN KEY (cd_municipio)         REFERENCES municipio(cd_municipio),
    FOREIGN KEY (nr_zona, cd_municipio) REFERENCES zona_eleitoral(nr_zona, cd_municipio),
    FOREIGN KEY (cd_cargo)             REFERENCES cargo(cd_cargo),
    FOREIGN KEY (nr_partido)           REFERENCES partido(nr_partido)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Índices para queries analíticas frequentes
CREATE INDEX idx_votacao_eleicao_cargo
    ON votacao_partido_munzona (cd_eleicao, nr_turno, cd_cargo);

CREATE INDEX idx_votacao_zona
    ON votacao_partido_munzona (nr_zona, cd_municipio);

CREATE INDEX idx_votacao_partido
    ON votacao_partido_munzona (nr_partido);

CREATE INDEX idx_votacao_municipio_cargo
    ON votacao_partido_munzona (cd_municipio, cd_cargo, cd_eleicao);

-- =============================================================================
-- Notas de design
-- =============================================================================
-- 1. zona_eleitoral tem PK composta (nr_zona, cd_municipio) porque o mesmo
--    número de zona pode existir em municípios diferentes.
--
-- 2. Coligação/federação fica desnormalizada na tabela fato porque sua
--    composição muda a cada eleição — normalizar criaria complexidade sem
--    ganho analítico para o projeto.
--
-- 3. O schema cobre votacao_partido_munzona. Para votacao_secao e
--    consulta_cand, tabelas adicionais seriam necessárias.
--
-- 4. Tipos de dados escolhidos para MySQL 8.0+.
-- =============================================================================
