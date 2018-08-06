USE [MSTOREAF_mstoreDemo]
GO

SET ANSI_NULLS ON
GO

SET QUOTED_IDENTIFIER ON
GO


-- =============================================
-- Author:		Neil Maude
-- Create date: 6th August 2018
-- Description:	Nasty bodge to update document refs with captured data

-- We will assume that CB_DREF1 contains the form unique ID, for demo purposes
-- Anyone who doesn't like self-generating SQL code, please look away now...

-- =============================================
CREATE TRIGGER [dbo].[setFormData] 
   ON  [dbo].[MICAB2]					-- Formation demo cabinet
   AFTER INSERT
AS 
BEGIN
	-- SET NOCOUNT ON added to prevent extra result sets from
	-- interfering with SELECT statements.
	SET NOCOUNT ON;

	DECLARE @SourceID varchar(255)
	DECLARE @TargetDTID int
	DECLARE @TargetDocID int 
	DECLARE @Counter smallint
	DECLARE @NumRefs smallint
	DECLARE @FieldName varchar(50)
	DECLARE @FieldValue varchar(50)
	DECLARE @LookupSQL varchar(MAX)

	DECLARE @sSQL nvarchar(500);
	DECLARE @ParamDefinition nvarchar(500);
	DECLARE @Tablename nvarchar(50)  

	DECLARE @FormDate as Date 

	SET @Tablename = N'zFormationData'								-- Source data table

	Set @SourceID = (SELECT Top 1 CB_DREF1 From inserted)			-- DREF #1 is the linking filename ref
																	-- This will match to a record in zFormationData
	Set @TargetDocID = (SELECT Top 1 CB_DOCID From inserted)

	-- Get the document type ID
	Set @TargetDTID = (SELECT top 1 CB_DTID From inserted)		 

	-- How many CB_CREFx values do we have?
	Set @NumRefs = (select TOP 1 CT_COMREFS from MICABDEF where CT_ID = '2')		-- Hardcoded to MICAB2...
	Set @Counter = 1
	WHILE (@Counter <= @NumRefs)
	BEGIN
		-- update this common reference - just copy across from zFormationData, which must have enough fields
		
		-- First get the @FieldValue
		SET @FieldName = 'CB_CREF' + CAST(@Counter as varchar(2)) 

		SET @sSQL = N'SELECT Top 1 @retvalOUT = ' + @Fieldname + ' FROM ' + @Tablename + ' where ID = ' + @SourceID;  
		SET @ParamDefinition = N'@retvalOUT varchar(50) OUTPUT';

		EXEC sp_executesql @sSQL, @ParamDefinition, @retvalOUT=@FieldValue OUTPUT;
		-- Now have the field value in @FieldValue

		-- Now do the update
		Set @sSQL = 'update MICAB2 set ' + @FieldName + ' = ' +  '''' + @FieldValue + '''' + ' where CB_DOCID = ' + CAST(@TargetDocID as varchar(50))
		exec sp_executesql @sSQL

		Set @Counter = @Counter + 1
	END

	---- Repeat for CB_DREFx values
	Set @NumRefs = (select TOP 1 DT_DOCREFS from MIDTMPLATE where DT_ID = @TargetDTID)		
	Set @Counter = 2	-- ignore the first document ref, as this is always the form ID!!!
	WHILE (@Counter <= @NumRefs)
	BEGIN
		-- update this document reference - just copy across from zFormationData, which must have enough fields
		
		-- First get the @FieldValue
		SET @FieldName = 'CB_DREF' + CAST(@Counter as varchar(2)) 
		
		SET @sSQL = N'SELECT Top 1 @retvalOUT = ' + @Fieldname + ' FROM ' + @Tablename + ' where ID = ' +  @SourceID
		SET @ParamDefinition = N'@retvalOUT varchar(50) OUTPUT';
		
		EXEC sp_executesql @sSQL, @ParamDefinition, @retvalOUT=@FieldValue OUTPUT;
		-- Now have the field value in @FieldValue
		
		-- Now do the update
		Set @sSQL = N'update MICAB2 set ' + @FieldName + ' = ' +  '''' + @FieldValue + '''' + ' where CB_DOCID = ' + CAST(@TargetDocID as varchar(50))
		exec sp_executesql @sSQL

		Set @Counter = @Counter + 1
	END

	-- Now deal with the date value for the form
	Set @FormDate = (select top 1 CB_DOCDATE from zFormationData where ID = @SourceID)
	IF ISDATE(Cast(@FormDate as varchar(50))) = 1
		update MICAB2 Set CB_DOCDATE = @FormDate Where CB_DOCID = @TargetDocID 

END

GO


