
-- Create the Formation forms demo data table
-- NeilM 6th August 2018

USE [MSTOREAF_mstoreDemo]
GO

/****** Object:  Table [dbo].[zFormationData]    Script Date: 06/08/2018 14:05:33 ******/
SET ANSI_NULLS ON
GO

SET QUOTED_IDENTIFIER ON
GO

CREATE TABLE [dbo].[zFormationData](
	[ID] [int] IDENTITY(1,1) NOT NULL,
	[filename] [varchar](max) NULL,
	[JSON] [ntext] NULL,
	[originalpath] [varchar](max) NULL,
	[CB_CREF1] [varchar](max) NULL,
	[CB_CREF2] [varchar](max) NULL,
	[CB_CREF3] [varchar](max) NULL,
	[CB_CREF4] [varchar](max) NULL,
	[CB_CREF5] [varchar](max) NULL,
	[CB_DREF1] [varchar](max) NULL,
	[CB_DREF2] [varchar](max) NULL,
	[CB_DREF3] [varchar](max) NULL,
	[CB_DREF4] [varchar](max) NULL,
	[CB_DREF5] [varchar](max) NULL,
	[CB_DREF6] [varchar](max) NULL,
	[CB_DREF7] [varchar](max) NULL,
	[CB_DREF8] [varchar](max) NULL,
	[CB_DREF9] [varchar](max) NULL,
	[CB_DREF10] [varchar](max) NULL,
	[CB_DOCDATE] [date] NULL,
	[formtype] [varchar](max) NULL,
	[formref] [varchar](max) NULL
) ON [PRIMARY] TEXTIMAGE_ON [PRIMARY]
GO

ALTER TABLE [dbo].[zFormationData] ADD  CONSTRAINT [DF_zFormationData_CB_DOCDATE]  DEFAULT (getdate()) FOR [CB_DOCDATE]
GO


