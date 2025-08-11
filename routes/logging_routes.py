# routes/logging_routes.py

from flask import Blueprint, request, jsonify, send_file
from services.action_logger import action_logger
import io
import datetime

logging_routes_bp = Blueprint('logging_routes', __name__)

@logging_routes_bp.route('/api/log_action', methods=['POST'])
def log_action():
    """
    Log an action from the frontend
    
    Expected JSON:
    {
        "timestamp": "2025-08-11T10:30:45.123Z",
        "action": "Scan rapide terminé",
        "status": "SUCCESS"
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No JSON data provided'}), 400
        
        action = data.get('action', 'Unknown action')
        status = data.get('status', 'SUCCESS')
        timestamp = data.get('timestamp')
        
        # Add client info as metadata
        metadata = {
            'client_ip': request.remote_addr,
            'user_agent': request.headers.get('User-Agent', 'Unknown'),
            'client_timestamp': timestamp
        }
        
        # Log the action
        success = action_logger.log_action(action, status, metadata)
        
        if success:
            return jsonify({'success': True, 'message': 'Action logged successfully'})
        else:
            return jsonify({'success': False, 'error': 'Failed to log action'}), 500
        
    except Exception as e:
        print(f"Log action error: {str(e)}")
        return jsonify({'success': False, 'error': f'Server error: {str(e)}'}), 500

@logging_routes_bp.route('/api/download_logs', methods=['GET'])
def download_logs():
    """
    Download logs as a text file
    
    Query parameters:
    - date: specific date (YYYY-MM-DD) or 'all' for all logs
    - format: 'json' or 'readable' (default: readable)
    """
    try:
        date_param = request.args.get('date', 'today')
        format_param = request.args.get('format', 'readable')
        
        if date_param == 'today':
            date_param = datetime.datetime.now().strftime('%Y-%m-%d')
        
        if date_param == 'all':
            # Get all log files and combine them
            all_files = action_logger.get_all_log_files()
            combined_content = []
            
            for filename in all_files:
                content = action_logger.get_log_file_content(filename)
                if content:
                    combined_content.append(f"\n{'='*60}")
                    combined_content.append(f"LOG FILE: {filename}")
                    combined_content.append('='*60)
                    combined_content.append(content)
            
            if not combined_content:
                return jsonify({'error': 'No log files found'}), 404
            
            content = '\n'.join(combined_content)
            filename = f'all_action_logs_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.txt'
            
        else:
            # Get specific date logs
            log_filename = f'actions_{date_param}.log'
            content = action_logger.get_log_file_content(log_filename)
            
            if not content:
                return jsonify({'error': f'No logs found for date: {date_param}'}), 404
            
            filename = f'action_logs_{date_param}.txt'
        
        # Create file-like object
        file_obj = io.BytesIO(content.encode('utf-8'))
        file_obj.seek(0)
        
        return send_file(
            file_obj,
            mimetype='text/plain',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        print(f"Download logs error: {str(e)}")
        return jsonify({'error': f'Failed to download logs: {str(e)}'}), 500

@logging_routes_bp.route('/api/get_logs', methods=['GET'])
def get_logs():
    """
    Get logs as JSON for viewing
    
    Query parameters:
    - date: specific date (YYYY-MM-DD)
    - limit: maximum number of entries
    """
    try:
        date_param = request.args.get('date')
        limit_param = request.args.get('limit', type=int)
        
        logs = action_logger.get_logs(date=date_param, limit=limit_param)
        
        return jsonify({
            'success': True,
            'logs': logs,
            'total': len(logs)
        })
        
    except Exception as e:
        print(f"Get logs error: {str(e)}")
        return jsonify({'success': False, 'error': f'Failed to get logs: {str(e)}'}), 500

@logging_routes_bp.route('/api/log_files', methods=['GET'])
def list_log_files():
    """
    Get list of available log files
    """
    try:
        files = action_logger.get_all_log_files()
        return jsonify({
            'success': True,
            'files': files
        })
        
    except Exception as e:
        print(f"List log files error: {str(e)}")
        return jsonify({'success': False, 'error': f'Failed to list log files: {str(e)}'}), 500

@logging_routes_bp.route('/api/log_stats', methods=['GET'])
def get_log_statistics():
    """
    Get statistics about logged actions
    """
    try:
        stats = action_logger.get_log_statistics()
        return jsonify({
            'success': True,
            'statistics': stats
        })
        
    except Exception as e:
        print(f"Get log statistics error: {str(e)}")
        return jsonify({'success': False, 'error': f'Failed to get statistics: {str(e)}'}), 500

@logging_routes_bp.route('/api/clear_logs', methods=['POST'])
def clear_logs():
    """
    Clear logs (admin function)
    
    Expected JSON:
    {
        "date": "2025-08-11" or "all",
        "confirm": true
    }
    """
    try:
        data = request.get_json()
        if not data or not data.get('confirm'):
            return jsonify({'success': False, 'error': 'Confirmation required'}), 400
        
        date_param = data.get('date', 'today')
        
        if date_param == 'all':
            # Clear all logs (dangerous operation)
            import shutil
            shutil.rmtree(action_logger.log_dir)
            action_logger.log_dir.mkdir(exist_ok=True)
            
            # Log this action
            action_logger.log_action('All logs cleared', 'SUCCESS', {'admin_action': True})
            
            return jsonify({'success': True, 'message': 'All logs cleared'})
        
        else:
            if date_param == 'today':
                date_param = datetime.datetime.now().strftime('%Y-%m-%d')
            
            # Clear specific date logs
            log_file = action_logger.log_dir / f'actions_{date_param}.log'
            readable_file = action_logger.log_dir / f'actions_{date_param}_readable.log'
            
            deleted_files = []
            if log_file.exists():
                log_file.unlink()
                deleted_files.append(log_file.name)
            
            if readable_file.exists():
                readable_file.unlink()
                deleted_files.append(readable_file.name)
            
            if deleted_files:
                action_logger.log_action(f'Logs cleared for {date_param}', 'SUCCESS', 
                                       {'admin_action': True, 'deleted_files': deleted_files})
                return jsonify({'success': True, 'message': f'Logs cleared for {date_param}', 'deleted_files': deleted_files})
            else:
                return jsonify({'success': False, 'error': f'No logs found for {date_param}'}), 404
        
    except Exception as e:
        print(f"Clear logs error: {str(e)}")
        action_logger.log_action(f'Failed to clear logs: {str(e)}', 'ERROR', {'admin_action': True})
        return jsonify({'success': False, 'error': f'Failed to clear logs: {str(e)}'}), 500

@logging_routes_bp.route('/api/cleanup_old_logs', methods=['POST'])
def cleanup_old_logs():
    """
    Cleanup logs older than specified days
    
    Expected JSON:
    {
        "days_to_keep": 30
    }
    """
    try:
        data = request.get_json()
        days_to_keep = data.get('days_to_keep', 30) if data else 30
        
        action_logger.cleanup_old_logs(days_to_keep)
        action_logger.log_action(f'Cleaned up logs older than {days_to_keep} days', 'SUCCESS', 
                               {'admin_action': True, 'days_to_keep': days_to_keep})
        
        return jsonify({'success': True, 'message': f'Cleaned up logs older than {days_to_keep} days'})
        
    except Exception as e:
        print(f"Cleanup old logs error: {str(e)}")
        return jsonify({'success': False, 'error': f'Failed to cleanup logs: {str(e)}'}), 500