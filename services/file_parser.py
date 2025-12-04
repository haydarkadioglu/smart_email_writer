import pandas as pd
import io
from typing import List, Dict, Optional, Tuple
from models.email_models import RecipientData


class FileParser:
    """Service for parsing CSV and Excel files to extract recipient data."""
    
    def __init__(self):
        self.supported_formats = ['.csv', '.xlsx', '.xls']
    
    def parse_file(self, file_content: bytes, filename: str, 
                   name_column: str, email_column: str, description_column: str,
                   custom_columns: Optional[Dict[str, str]] = None) -> List[RecipientData]:
        """
        Parse uploaded file and extract recipient data.
        
        Args:
            file_content: Raw file content as bytes
            filename: Original filename
            name_column: Column name containing recipient names
            email_column: Column name containing email addresses
            description_column: Column name containing descriptions
            custom_columns: Optional mapping of custom column names to field names
        
        Returns:
            List of RecipientData objects
        """
        try:
            # Determine file type and read accordingly
            file_extension = filename.lower().split('.')[-1]
            
            if file_extension == 'csv':
                df = pd.read_csv(io.BytesIO(file_content), encoding='utf-8')
            elif file_extension in ['xlsx', 'xls']:
                df = pd.read_excel(io.BytesIO(file_content))
            else:
                raise ValueError(f"Unsupported file format: {file_extension}")
            
            # Validate required columns exist
            required_columns = [name_column, email_column, description_column]
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                raise ValueError(f"Missing required columns: {missing_columns}")
            
            # Extract recipient data
            recipients = []
            for _, row in df.iterrows():
                # Get custom fields if provided
                custom_fields = {}
                if custom_columns:
                    for field_name, column_name in custom_columns.items():
                        if column_name in df.columns:
                            custom_fields[field_name] = str(row[column_name]) if pd.notna(row[column_name]) else ""
                
                recipient = RecipientData(
                    name=str(row[name_column]) if pd.notna(row[name_column]) else "",
                    email=str(row[email_column]) if pd.notna(row[email_column]) else "",
                    description=str(row[description_column]) if pd.notna(row[description_column]) else "",
                    custom_fields=custom_fields if custom_fields else None
                )
                recipients.append(recipient)
            
            return recipients
            
        except Exception as e:
            raise Exception(f"Error parsing file: {str(e)}")
    
    def get_file_columns(self, file_content: bytes, filename: str) -> List[str]:
        """
        Get column names from uploaded file without parsing all data.
        
        Args:
            file_content: Raw file content as bytes
            filename: Original filename
        
        Returns:
            List of column names
        """
        try:
            file_extension = filename.lower().split('.')[-1]
            
            if file_extension == 'csv':
                df = pd.read_csv(io.BytesIO(file_content), nrows=0, encoding='utf-8')
            elif file_extension in ['xlsx', 'xls']:
                df = pd.read_excel(io.BytesIO(file_content), nrows=0)
            else:
                raise ValueError(f"Unsupported file format: {file_extension}")
            
            return df.columns.tolist()
            
        except Exception as e:
            raise Exception(f"Error reading file columns: {str(e)}")
    
    def preview_data(self, file_content: bytes, filename: str, 
                    name_column: str, email_column: str, description_column: str,
                    custom_columns: Optional[Dict[str, str]] = None, 
                    preview_rows: int = 5) -> Tuple[List[Dict], int]:
        """
        Preview parsed data without creating full recipient objects.
        
        Args:
            file_content: Raw file content as bytes
            filename: Original filename
            name_column: Column name containing recipient names
            email_column: Column name containing email addresses
            description_column: Column name containing descriptions
            custom_columns: Optional mapping of custom column names to field names
            preview_rows: Number of rows to preview
        
        Returns:
            Tuple of (preview_data, total_rows)
        """
        try:
            file_extension = filename.lower().split('.')[-1]
            
            if file_extension == 'csv':
                df = pd.read_csv(io.BytesIO(file_content), encoding='utf-8')
            elif file_extension in ['xlsx', 'xls']:
                df = pd.read_excel(io.BytesIO(file_content))
            else:
                raise ValueError(f"Unsupported file format: {file_extension}")
            
            total_rows = len(df)
            preview_df = df.head(preview_rows)
            
            preview_data = []
            for _, row in preview_df.iterrows():
                row_data = {
                    'name': str(row[name_column]) if pd.notna(row[name_column]) else "",
                    'email': str(row[email_column]) if pd.notna(row[email_column]) else "",
                    'description': str(row[description_column]) if pd.notna(row[description_column]) else ""
                }
                
                # Add custom fields if provided
                if custom_columns:
                    for field_name, column_name in custom_columns.items():
                        if column_name in df.columns:
                            row_data[field_name] = str(row[column_name]) if pd.notna(row[column_name]) else ""
                
                preview_data.append(row_data)
            
            return preview_data, total_rows
            
        except Exception as e:
            raise Exception(f"Error previewing file data: {str(e)}")
    
    def validate_email_addresses(self, recipients: List[RecipientData]) -> Tuple[List[RecipientData], List[str]]:
        """
        Validate email addresses and return valid recipients with invalid ones.
        
        Args:
            recipients: List of RecipientData objects
        
        Returns:
            Tuple of (valid_recipients, invalid_emails)
        """
        import re
        
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        valid_recipients = []
        invalid_emails = []
        
        for recipient in recipients:
            if recipient.email and re.match(email_pattern, recipient.email):
                valid_recipients.append(recipient)
            else:
                invalid_emails.append(f"{recipient.name} ({recipient.email})")
        
        return valid_recipients, invalid_emails
