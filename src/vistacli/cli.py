"""Command-line interface for Vista Social tools."""

import csv
import json
import logging
import sys
from typing import Optional

import click

from .auth import VSAuth
from .api import VSApi
from .upload import VSUploader, SUPPORTED_EXTENSIONS

# Configure logging
logging.basicConfig(
    level=logging.WARNING,
    format='%(name)s: %(message)s'
)


@click.group()
@click.option('--log-level', 
              type=click.Choice(['DEBUG', 'INFO', 'WARNING', 'ERROR'], case_sensitive=False),
              default='WARNING',
              help='Set logging level')
def cli(log_level: str):
    """Vista Social CLI tools."""
    logging.getLogger().setLevel(getattr(logging, log_level.upper()))


@cli.command()
@click.option('--auth-file', 
              type=click.Path(path_type=str),
              help='Path to auth file (default: ~/.vsauth)')
@click.option('--log-level', 
              type=click.Choice(['DEBUG', 'INFO', 'WARNING', 'ERROR'], case_sensitive=False),
              default='WARNING',
              help='Set logging level')
def vsauth(auth_file: Optional[str], log_level: str):
    """Extract Vista Social cookies from Firefox and save them."""
    # Set logging level for this command
    logging.getLogger().setLevel(getattr(logging, log_level.upper()))
    
    try:
        auth = VSAuth(Path(auth_file) if auth_file else None)
        
        # Extract cookies from Firefox
        cookies = auth.extract_cookies()
        
        # Save cookies to file
        auth.save_cookies(cookies)
        
        click.echo(f"Successfully extracted {len(cookies)} cookies from Firefox")
        click.echo(f"Cookies saved to: {auth.auth_file}")
        
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.group()
def vsdir():
    """Manage folders on Vista Social."""
    pass


@vsdir.command()
@click.argument('folder_name')
@click.option('--description', '-d', default='', help='Description of the folder')
@click.option('--labels', '-l', multiple=True, help='Labels/tags for the folder (can specify multiple)')
@click.option('--entity-gids', '-e', multiple=True, help='Entity GIDs for the folder (can specify multiple)')
@click.option('--media-path', '-m', help='Parent folder ID for creating subfolders')
@click.option('--auth-file', 
              type=click.Path(path_type=str),
              help='Path to auth file (default: ~/.vsauth)')
@click.option('--log-level', 
              type=click.Choice(['DEBUG', 'INFO', 'WARNING', 'ERROR'], case_sensitive=False),
              default='WARNING',
              help='Set logging level')
def add(folder_name: str, description: str, labels: tuple, entity_gids: tuple, media_path: Optional[str], auth_file: Optional[str], log_level: str):
    """Add a new folder."""
    # Set logging level for this command
    logging.getLogger().setLevel(getattr(logging, log_level.upper()))
    
    try:
        auth = VSAuth(auth_file=Path(auth_file) if auth_file else None)
        with VSApi(auth=auth) as api:
            result = api.create_folder(
                name=folder_name,
                description=description,
                labels=list(labels) if labels else None,
                entity_gids=list(entity_gids) if entity_gids else None,
                media_path=media_path
            )
            click.echo(f"Successfully created folder: {folder_name}")
            
    except Exception as e:
        click.echo(f"Error creating folder: {e}", err=True)
        sys.exit(1)


@vsdir.command(name='list')
@click.option('--json', '-j', 'json_output', is_flag=True, help='Output in JSON format')
@click.option('--csv', '-c', 'csv_output', is_flag=True, help='Output in CSV format')
@click.option('--media-path', '-m', help='Parent folder ID for subfolder listing')
@click.option('--auth-file', 
              type=click.Path(path_type=str),
              help='Path to auth file (default: ~/.vsauth)')
@click.option('--log-level', 
              type=click.Choice(['DEBUG', 'INFO', 'WARNING', 'ERROR'], case_sensitive=False),
              default='WARNING',
              help='Set logging level')
def list_folders(json_output: bool, csv_output: bool, media_path: Optional[str], auth_file: Optional[str], log_level: str):
    """List folders."""
    # Set logging level for this command
    logging.getLogger().setLevel(getattr(logging, log_level.upper()))
    
    try:
        auth = VSAuth(auth_file=Path(auth_file) if auth_file else None)
        with VSApi(auth=auth) as api:
            folders = api.get_folders(media_path=media_path)
            
            if json_output:
                # Output full JSON response
                click.echo(json.dumps(folders, indent=2))
            elif csv_output:
                # Output CSV format: title,id,created_at
                writer = csv.writer(sys.stdout)
                for folder in folders:
                    writer.writerow([
                        folder.get('title', ''),
                        folder.get('id', ''),
                        folder.get('created_at', '')
                    ])
            else:
                # Output just titles, lexically sorted
                titles = sorted([folder.get('title', '') for folder in folders])
                for title in titles:
                    click.echo(title)
                    
    except Exception as e:
        click.echo(f"Error listing folders: {e}", err=True)
        sys.exit(1)





@vsdir.command()
@click.argument('folder_id')
@click.option('--auth-file', 
              type=click.Path(path_type=str),
              help='Path to auth file (default: ~/.vsauth)')
@click.option('--log-level', 
              type=click.Choice(['DEBUG', 'INFO', 'WARNING', 'ERROR'], case_sensitive=False),
              default='WARNING',
              help='Set logging level')
def delete(folder_id: str, auth_file: Optional[str], log_level: str):
    """Delete a folder by ID."""
    # Set logging level for this command
    logging.getLogger().setLevel(getattr(logging, log_level.upper()))
    
    try:
        auth = VSAuth(auth_file=Path(auth_file) if auth_file else None)
        with VSApi(auth=auth) as api:
            api.delete_folder(folder_id)
            click.echo(f"Successfully deleted folder: {folder_id}")
            
    except Exception as e:
        click.echo(f"Error deleting folder: {e}", err=True)
        sys.exit(1)


# Add missing import
from pathlib import Path


@cli.command()
@click.argument('file_paths', nargs=-1, type=click.Path(exists=True, path_type=str), required=True)
@click.option('--subfolder', '-s', help='Subfolder ID to place the uploaded asset in')
@click.option('--auth-file', 
              type=click.Path(path_type=str),
              help='Path to auth file (default: ~/.vsauth)')
@click.option('--log-level', 
              type=click.Choice(['DEBUG', 'INFO', 'WARNING', 'ERROR'], case_sensitive=False),
              default='WARNING',
              help='Set logging level')
def vsput(file_paths: tuple, subfolder: Optional[str], auth_file: Optional[str], log_level: str):
    """Upload files to Vista Social media library."""
    # Set logging level for this command
    logging.getLogger().setLevel(getattr(logging, log_level.upper()))
    
    try:
        # Initialize auth and uploader
        auth = VSAuth(auth_file=Path(auth_file) if auth_file else None)
        uploader = VSUploader(auth)
        
        # Track results
        successful_uploads = []
        failed_uploads = []
        
        # Upload each file
        for file_path in file_paths:
            try:
                # Upload the file
                result = uploader.upload_file(file_path, subfolder)
                
                # Output success message with file info
                file_name = Path(file_path).name
                click.echo(f"Successfully uploaded: {file_name}")
                
                # In debug mode, show more details
                if log_level.upper() == 'DEBUG':
                    click.echo(f"Media GID: {result.get('media_gid', 'N/A')}")
                    click.echo(f"Temp ID: {result.get('tempId', 'N/A')}")
                
                successful_uploads.append(file_path)
                
            except ValueError as e:
                file_name = Path(file_path).name
                click.echo(f"Validation error for {file_name}: {e}", err=True)
                click.echo(f"Supported file types: {', '.join(SUPPORTED_EXTENSIONS)}", err=True)
                failed_uploads.append(file_path)
            except FileNotFoundError as e:
                file_name = Path(file_path).name
                click.echo(f"File not found: {file_name} - {e}", err=True)
                failed_uploads.append(file_path)
            except Exception as e:
                file_name = Path(file_path).name
                click.echo(f"Error uploading {file_name}: {e}", err=True)
                failed_uploads.append(file_path)
        
        # Summary
        if successful_uploads:
            click.echo(f"\nSuccessfully uploaded {len(successful_uploads)} file(s)")
        if failed_uploads:
            click.echo(f"Failed to upload {len(failed_uploads)} file(s)", err=True)
            sys.exit(1)
            
    except Exception as e:
        click.echo(f"Error initializing uploader: {e}", err=True)
        sys.exit(1) 