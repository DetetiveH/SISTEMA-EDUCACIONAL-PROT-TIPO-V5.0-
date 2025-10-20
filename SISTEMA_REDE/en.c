#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include <time.h>

// Headers de Socket e Threads específicos para cada SO
#ifdef _WIN32
#include <winsock2.h>
#include <ws2tcpip.h>
#include <process.h> 
#pragma comment(lib, "ws2_32.lib") 
#else
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <unistd.h>
#include <pthread.h> 
#endif

// Headers para criação de diretórios (multiplataforma)
#ifdef _WIN32
#include <direct.h>
#else
#include <sys/stat.h>
#include <sys/types.h>
#endif

// =============================================================================
// ARQUITETURA DO SERVIDOR
// -----------------------------------------------------------------------------
// Este servidor utiliza uma arquitetura multi-threaded para lidar com múltiplos
// clientes simultaneamente. Cada cliente que se conecta é gerido numa thread
// separada.
//
// THREAD SAFETY:
// Para evitar condições de corrida (race conditions) e corrupção de dados
// durante o acesso aos ficheiros CSV por múltiplas threads, foi implementado
// um MUTEX GLOBAL (`g_file_mutex`). Todas as funções que realizam operações
// de leitura ou escrita em ficheiros devem bloquear este mutex antes de
// aceder ao ficheiro e libertá-lo após a conclusão da operação. Isto garante
// que o acesso aos ficheiros seja serializado e seguro.
// =============================================================================


// --- Constantes do Servidor e Arquivos ---
#define PORTA 8080
#define TAMANHO_BUFFER 4096
#define ARQUIVO_CURSOS "cursos.csv"
#define ARQUIVO_MATERIAS "materias.csv"
#define ARQUIVO_TURMAS "turmas.csv"
#define ARQUIVO_ALUNOS "alunos.csv"
#define ARQUIVO_ATIVIDADES "atividades.csv"
#define ARQUIVO_NOTAS "notas.csv"
#define ARQUIVO_MENSAGENS "mensagens.csv"
#define ARQUIVO_LOG "log.csv"
#define MAX_LINHA 1024

// --- Mutex Global para Thread Safety ---
#ifdef _WIN32
CRITICAL_SECTION g_file_mutex;
#else
pthread_mutex_t g_file_mutex = PTHREAD_MUTEX_INITIALIZER;
#endif


// --- Protótipos das Funções do Servidor ---
void iniciar_servidor();
char* processar_comando(char* buffer);
#ifdef _WIN32
unsigned __stdcall connection_handler_win(void *socket_desc);
#else
void *connection_handler(void *socket_desc);
#endif
void processar_cliente(int client_socket);


// --- Protótipos das Funções Utilitárias ---
int id_existe(const char* nome_arquivo, int id_para_verificar);
int gerar_id_unico(const char* nome_arquivo);
int verificar_alunos_na_turma(int id_turma);
int verificar_materias_no_curso(int id_curso);


// --- MÓDULO DE CURSOS: Protótipos ---
char* cadastrar_curso_handler(char* args);
char* listar_cursos_handler();
char* excluir_curso_handler(char* args);

// --- MÓDULO DE MATÉRIAS: Protótipos ---
char* cadastrar_materia_handler(char* args);
char* listar_materias_handler();

// --- MÓDULO DE TURMAS: Protótipos ---
char* cadastrar_turma_handler(char* args);
char* listar_turmas_handler();
char* excluir_turma_handler(char* args);

// --- MÓDULO DE ALUNOS: Protótipos ---
char* cadastrar_aluno_handler(char* args);
char* listar_alunos_handler();
char* excluir_aluno_handler(char* args);

// --- MÓDULO DE ATIVIDADES: Protótipos ---
char* cadastrar_atividade_handler(char* args);
char* listar_atividades_handler();

// --- MÓDULO DE NOTAS: Protótipos ---
char* cadastrar_nota_handler(char* args);
char* listar_notas_handler();

// --- MÓDULO DE DIÁRIO: Protótipos ---
char* registrar_aula_handler(char* args);
char* listar_diario_handler(char* args);

// --- MÓDULO DE MENSAGENS: Protótipos ---
char* postar_mensagem_handler(char* args);
char* listar_mensagens_handler();

// --- MÓDULO DE SISTEMA (IA, LOG, BACKUP): Protótipos ---
char* analisar_desempenho_ia_handler();
char* log_handler(char* args);
char* listar_logs_handler();
char* backup_handler();
char* limpar_arquivo_handler(const char* nome_arquivo);


// --- Função Principal ---
int main() {
    srand(time(NULL));
    #ifdef _WIN32
    InitializeCriticalSection(&g_file_mutex);
    #endif
    iniciar_servidor();
    return 0;
}

// --- Implementação da Lógica do Servidor ---

void iniciar_servidor() {
    int server_fd, client_socket;
    struct sockaddr_in address;
    int addrlen = sizeof(address);

#ifdef _WIN32
    WSADATA wsa;
    if (WSAStartup(MAKEWORD(2, 2), &wsa) != 0) {
        printf("Falha ao inicializar o Winsock. Erro: %d\n", WSAGetLastError());
        return;
    }
#endif

    if ((server_fd = socket(AF_INET, SOCK_STREAM, 0)) == 0) {
        perror("Socket falhou");
        exit(EXIT_FAILURE);
    }

    address.sin_family = AF_INET;
    address.sin_addr.s_addr = INADDR_ANY;
    address.sin_port = htons(PORTA);

    if (bind(server_fd, (struct sockaddr*)&address, sizeof(address)) < 0) {
        perror("Bind falhou");
        exit(EXIT_FAILURE);
    }

    if (listen(server_fd, 10) < 0) {
        perror("Listen falhou");
        exit(EXIT_FAILURE);
    }

    printf("Servidor C iniciado na porta %d. Aguardando clientes...\n", PORTA);

    while (1) {
        if ((client_socket = accept(server_fd, (struct sockaddr*)&address, (socklen_t*)&addrlen)) < 0) {
            perror("Accept falhou");
            continue;
        }
        
        printf("Novo cliente conectado. Atribuindo a um handler...\n");

        int *new_sock = malloc(sizeof(int));
        *new_sock = client_socket;

#ifdef _WIN32
        HANDLE thread_handle;
        thread_handle = (HANDLE)_beginthreadex(NULL, 0, &connection_handler_win, (void*)new_sock, 0, NULL);
        if (thread_handle == 0) {
            perror("Nao foi possivel criar a thread do Windows");
        } else {
            CloseHandle(thread_handle);
        }
#else
        pthread_t sniffer_thread;
        if(pthread_create(&sniffer_thread, NULL, connection_handler, (void*) new_sock) < 0) {
            perror("Nao foi possivel criar a thread do pthreads");
        } else {
            pthread_detach(sniffer_thread);
        }
#endif
    }

#ifdef _WIN32
    closesocket(server_fd);
    DeleteCriticalSection(&g_file_mutex);
    WSACleanup();
#else
    close(server_fd);
#endif
}

#ifdef _WIN32
unsigned __stdcall connection_handler_win(void *socket_desc) {
    int sock = *(int*)socket_desc;
    free(socket_desc);
    processar_cliente(sock);
    return 0;
}
#else
void *connection_handler(void *socket_desc) {
    int sock = *(int*)socket_desc;
    free(socket_desc);
    processar_cliente(sock);
    pthread_exit(NULL);
    return NULL;
}
#endif

void processar_cliente(int client_socket) {
    char buffer[TAMANHO_BUFFER] = {0};
    int bytes_lidos;

    while ((bytes_lidos = recv(client_socket, buffer, TAMANHO_BUFFER, 0)) > 0) {
        buffer[bytes_lidos] = '\0';
        printf("Comando recebido: %s\n", buffer);

        char* resposta = processar_comando(buffer);
        
        send(client_socket, resposta, strlen(resposta), 0);
        printf("Resposta enviada.\n");

        free(resposta);
        memset(buffer, 0, TAMANHO_BUFFER);
    }

    printf("Cliente desconectado.\n");
#ifdef _WIN32
    closesocket(client_socket);
#else
    close(client_socket);
#endif
}

char* processar_comando(char* buffer) {
    char buffer_copia[TAMANHO_BUFFER];
    strcpy(buffer_copia, buffer);

    char* comando = strtok(buffer_copia, ";");
    char* args = strtok(NULL, "");
    char* resposta = NULL;

    // Roteamento de comandos para os handlers apropriados
    if (strcmp(comando, "LISTAR_CURSOS") == 0) resposta = listar_cursos_handler();
    else if (strcmp(comando, "CADASTRAR_CURSO") == 0) resposta = cadastrar_curso_handler(args);
    else if (strcmp(comando, "EXCLUIR_CURSO") == 0) resposta = excluir_curso_handler(args);
    else if (strcmp(comando, "LISTAR_MATERIAS") == 0) resposta = listar_materias_handler();
    else if (strcmp(comando, "CADASTRAR_MATERIA") == 0) resposta = cadastrar_materia_handler(args);
    else if (strcmp(comando, "LISTAR_TURMAS") == 0) resposta = listar_turmas_handler();
    else if (strcmp(comando, "CADASTRAR_TURMA") == 0) resposta = cadastrar_turma_handler(args);
    else if (strcmp(comando, "EXCLUIR_TURMA") == 0) resposta = excluir_turma_handler(args);
    else if (strcmp(comando, "LISTAR_ALUNOS") == 0) resposta = listar_alunos_handler();
    else if (strcmp(comando, "CADASTRAR_ALUNO") == 0) resposta = cadastrar_aluno_handler(args);
    else if (strcmp(comando, "EXCLUIR_ALUNO") == 0) resposta = excluir_aluno_handler(args);
    else if (strcmp(comando, "CADASTRAR_ATIVIDADE") == 0) resposta = cadastrar_atividade_handler(args);
    else if (strcmp(comando, "LISTAR_ATIVIDADES") == 0) resposta = listar_atividades_handler();
    else if (strcmp(comando, "CADASTRAR_NOTA") == 0) resposta = cadastrar_nota_handler(args);
    else if (strcmp(comando, "LISTAR_NOTAS_TODOS") == 0) resposta = listar_notas_handler();
    else if (strcmp(comando, "REGISTRAR_AULA") == 0) resposta = registrar_aula_handler(args);
    else if (strcmp(comando, "POSTAR_MENSAGEM") == 0) resposta = postar_mensagem_handler(args);
    else if (strcmp(comando, "LISTAR_MENSAGENS") == 0) resposta = listar_mensagens_handler();
    else if (strcmp(comando, "LOG") == 0) resposta = log_handler(args);
    else if (strcmp(comando, "LISTAR_LOGS") == 0) resposta = listar_logs_handler();
    else if (strcmp(comando, "BACKUP") == 0) resposta = backup_handler();
    else if (strcmp(comando, "ANALISAR_IA") == 0) resposta = analisar_desempenho_ia_handler();
    else if (strcmp(comando, "LIMPAR_NOTAS") == 0) resposta = limpar_arquivo_handler(ARQUIVO_NOTAS);
    else if (strcmp(comando, "LIMPAR_MENSAGENS") == 0) resposta = limpar_arquivo_handler(ARQUIVO_MENSAGENS);
    else if (strcmp(comando, "LIMPAR_LOGS") == 0) resposta = limpar_arquivo_handler(ARQUIVO_LOG);
    else if (strcmp(comando, "LISTAR_DIARIO") == 0) resposta = listar_diario_handler(args);
    else {
        resposta = malloc(100);
        sprintf(resposta, "ERRO;Comando '%s' nao reconhecido.", comando);
    }
    
    return resposta;
}


// --- GESTÃO DE CURSOS ---
char* cadastrar_curso_handler(char* args) {
    char nome_curso[100];
    char* resposta = malloc(256);

    if (sscanf(args, "%99[^\n]", nome_curso) != 1) {
        sprintf(resposta, "ERRO;Formato de argumentos invalido para CADASTRAR_CURSO.");
        return resposta;
    }
    
#ifdef _WIN32
    EnterCriticalSection(&g_file_mutex);
#else
    pthread_mutex_lock(&g_file_mutex);
#endif

    FILE *arquivo = fopen(ARQUIVO_CURSOS, "a");
    if (arquivo == NULL) {
        sprintf(resposta, "ERRO;Nao foi possivel abrir o arquivo de cursos.");
    } else {
        int id_curso = gerar_id_unico(ARQUIVO_CURSOS);
        fprintf(arquivo, "%d;%s\n", id_curso, nome_curso);
        fclose(arquivo);
        sprintf(resposta, "SUCESSO;Curso '%s' cadastrado com ID %d.", nome_curso, id_curso);
    }

#ifdef _WIN32
    LeaveCriticalSection(&g_file_mutex);
#else
    pthread_mutex_unlock(&g_file_mutex);
#endif

    return resposta;
}

char* listar_cursos_handler() {
#ifdef _WIN32
    EnterCriticalSection(&g_file_mutex);
#else
    pthread_mutex_lock(&g_file_mutex);
#endif
    FILE *arquivo = fopen(ARQUIVO_CURSOS, "r");
    if (arquivo == NULL) {
#ifdef _WIN32
        LeaveCriticalSection(&g_file_mutex);
#else
        pthread_mutex_unlock(&g_file_mutex);
#endif
        char* resp = malloc(50);
        strcpy(resp, "VAZIO;Nenhum curso cadastrado.");
        return resp;
    }
    
    char* resposta = malloc(TAMANHO_BUFFER * 2);
    strcpy(resposta, "DADOS;");
    char linha[MAX_LINHA];

    while (fgets(linha, sizeof(linha), arquivo)) {
        linha[strcspn(linha, "\n")] = 0;
        strcat(resposta, linha);
        strcat(resposta, "|");
    }
    fclose(arquivo);

#ifdef _WIN32
    LeaveCriticalSection(&g_file_mutex);
#else
    pthread_mutex_unlock(&g_file_mutex);
#endif

    if(strlen(resposta) > 6) {
        resposta[strlen(resposta) - 1] = '\0';
    }
    
    return resposta;
}

char* excluir_curso_handler(char* args) {
    int id_excluir;
    char* resposta = malloc(200);

    if (sscanf(args, "%d", &id_excluir) != 1) {
        sprintf(resposta, "ERRO;ID do curso invalido.");
        return resposta;
    }
    
#ifdef _WIN32
    EnterCriticalSection(&g_file_mutex);
#else
    pthread_mutex_lock(&g_file_mutex);
#endif

    if (verificar_materias_no_curso(id_excluir)) {
        sprintf(resposta, "ERRO;Nao e possivel excluir, existem materias associadas a este curso.");
    } else {
        FILE* original = fopen(ARQUIVO_CURSOS, "r");
        FILE* temp = fopen("temp_cursos.csv", "w");
        if (!original || !temp) {
            sprintf(resposta, "ERRO;Falha ao abrir arquivos temporarios.");
        } else {
            char linha[MAX_LINHA];
            while (fgets(linha, sizeof(linha), original)) {
                int id_atual;
                sscanf(linha, "%d", &id_atual);
                if (id_atual != id_excluir) {
                    fputs(linha, temp);
                }
            }
            fclose(original);
            fclose(temp);
            
            remove(ARQUIVO_CURSOS);
            rename("temp_cursos.csv", ARQUIVO_CURSOS);
            
            sprintf(resposta, "SUCESSO;Curso com ID %d excluido.", id_excluir);
        }
    }

#ifdef _WIN32
    LeaveCriticalSection(&g_file_mutex);
#else
    pthread_mutex_unlock(&g_file_mutex);
#endif

    return resposta;
}


// --- GESTÃO DE MATÉRIAS ---
char* cadastrar_materia_handler(char* args) {
    int id_curso;
    char nome_materia[100], prof_usuario[100], modalidade[20];
    char* resposta = malloc(256);

    if (sscanf(args, "%99[^;];%d;%99[^;];%19[^\n]", nome_materia, &id_curso, prof_usuario, modalidade) != 4) {
        sprintf(resposta, "ERRO;Formato de argumentos invalido para CADASTRAR_MATERIA.");
        return resposta;
    }

#ifdef _WIN32
    EnterCriticalSection(&g_file_mutex);
#else
    pthread_mutex_lock(&g_file_mutex);
#endif

    if (!id_existe(ARQUIVO_CURSOS, id_curso)) {
        sprintf(resposta, "ERRO;O curso com ID %d nao existe.", id_curso);
    } else {
        FILE *arquivo = fopen(ARQUIVO_MATERIAS, "a");
        if (arquivo == NULL) {
            sprintf(resposta, "ERRO;Nao foi possivel abrir o arquivo de materias.");
        } else {
            int id_materia = gerar_id_unico(ARQUIVO_MATERIAS);
            fprintf(arquivo, "%d;%s;%d;%s;%s\n", id_materia, nome_materia, id_curso, prof_usuario, modalidade);
            fclose(arquivo);
            sprintf(resposta, "SUCESSO;Materia '%s' cadastrada com ID %d.", nome_materia, id_materia);
        }
    }

#ifdef _WIN32
    LeaveCriticalSection(&g_file_mutex);
#else
    pthread_mutex_unlock(&g_file_mutex);
#endif

    return resposta;
}

char* listar_materias_handler() {
#ifdef _WIN32
    EnterCriticalSection(&g_file_mutex);
#else
    pthread_mutex_lock(&g_file_mutex);
#endif

    FILE *arquivo = fopen(ARQUIVO_MATERIAS, "r");
    if (arquivo == NULL) {
#ifdef _WIN32
        LeaveCriticalSection(&g_file_mutex);
#else
        pthread_mutex_unlock(&g_file_mutex);
#endif
        char* resp = malloc(50);
        strcpy(resp, "VAZIO;Nenhuma materia cadastrada.");
        return resp;
    }
    
    char* resposta = malloc(TAMANHO_BUFFER * 3);
    strcpy(resposta, "DADOS;");
    char linha[MAX_LINHA];
    while (fgets(linha, sizeof(linha), arquivo)) {
        linha[strcspn(linha, "\n")] = 0;
        strcat(resposta, linha);
        strcat(resposta, "|");
    }
    fclose(arquivo);

#ifdef _WIN32
    LeaveCriticalSection(&g_file_mutex);
#else
    pthread_mutex_unlock(&g_file_mutex);
#endif

    if(strlen(resposta) > 6) {
        resposta[strlen(resposta) - 1] = '\0';
    }
    
    return resposta;
}


// --- GESTÃO DE TURMAS ---
char* cadastrar_turma_handler(char* args) {
    char data[20], professor[100];
    char* resposta = malloc(256);

    if (sscanf(args, "%19[^;];%99[^\n]", data, professor) != 2) {
        sprintf(resposta, "ERRO;Formato de argumentos invalido para CADASTRAR_TURMA.");
        return resposta;
    }

#ifdef _WIN32
    EnterCriticalSection(&g_file_mutex);
#else
    pthread_mutex_lock(&g_file_mutex);
#endif

    FILE *arquivo = fopen(ARQUIVO_TURMAS, "a");
    if (arquivo == NULL) {
        sprintf(resposta, "ERRO;Nao foi possivel abrir o arquivo de turmas.");
    } else {
        int id_turma = gerar_id_unico(ARQUIVO_TURMAS);
        fprintf(arquivo, "%d;%s;%s\n", id_turma, data, professor);
        fclose(arquivo);
        sprintf(resposta, "SUCESSO;Turma para data '%s' cadastrada com ID %d.", data, id_turma);
    }
    
#ifdef _WIN32
    LeaveCriticalSection(&g_file_mutex);
#else
    pthread_mutex_unlock(&g_file_mutex);
#endif
    return resposta;
}

char* listar_turmas_handler() {
#ifdef _WIN32
    EnterCriticalSection(&g_file_mutex);
#else
    pthread_mutex_lock(&g_file_mutex);
#endif
    FILE *arquivo = fopen(ARQUIVO_TURMAS, "r");
    if (arquivo == NULL) {
#ifdef _WIN32
        LeaveCriticalSection(&g_file_mutex);
#else
        pthread_mutex_unlock(&g_file_mutex);
#endif
        char* resp = malloc(50);
        strcpy(resp, "VAZIO;Nenhuma turma cadastrada.");
        return resp;
    }
    
    char* resposta = malloc(TAMANHO_BUFFER * 2);
    strcpy(resposta, "DADOS;");
    char linha[MAX_LINHA];

    while (fgets(linha, sizeof(linha), arquivo)) {
        linha[strcspn(linha, "\n")] = 0;
        strcat(resposta, linha);
        strcat(resposta, "|");
    }
    fclose(arquivo);

#ifdef _WIN32
    LeaveCriticalSection(&g_file_mutex);
#else
    pthread_mutex_unlock(&g_file_mutex);
#endif

    if(strlen(resposta) > 6) {
        resposta[strlen(resposta) - 1] = '\0';
    }
    
    return resposta;
}

char* excluir_turma_handler(char* args) {
    int id_excluir;
    char* resposta = malloc(200);

    if (sscanf(args, "%d", &id_excluir) != 1) {
        sprintf(resposta, "ERRO;ID da turma invalido.");
        return resposta;
    }
    
#ifdef _WIN32
    EnterCriticalSection(&g_file_mutex);
#else
    pthread_mutex_lock(&g_file_mutex);
#endif
    
    if (!id_existe(ARQUIVO_TURMAS, id_excluir)) {
        sprintf(resposta, "ERRO;Turma com ID %d nao encontrada.", id_excluir);
    } else if (verificar_alunos_na_turma(id_excluir)) {
        sprintf(resposta, "ERRO;Nao e possivel excluir, existem alunos matriculados na turma %d.", id_excluir);
    } else {
        FILE* original = fopen(ARQUIVO_TURMAS, "r");
        FILE* temp = fopen("temp_turmas.csv", "w");
        if (!original || !temp) {
            sprintf(resposta, "ERRO;Falha ao abrir arquivos temporarios.");
        } else {
            char linha[MAX_LINHA];
            while (fgets(linha, sizeof(linha), original)) {
                int id_atual;
                sscanf(linha, "%d", &id_atual);
                if (id_atual != id_excluir) {
                    fputs(linha, temp);
                }
            }
            fclose(original);
            fclose(temp);
            
            remove(ARQUIVO_TURMAS);
            rename("temp_turmas.csv", ARQUIVO_TURMAS);
            
            sprintf(resposta, "SUCESSO;Turma com ID %d excluida.", id_excluir);
        }
    }

#ifdef _WIN32
    LeaveCriticalSection(&g_file_mutex);
#else
    pthread_mutex_unlock(&g_file_mutex);
#endif

    return resposta;
}


// --- GESTÃO DE ALUNOS ---
char* cadastrar_aluno_handler(char* args) {
    char nome[100], email[50];
    int idade, id_turma;
    char* resposta = malloc(256);

    if (sscanf(args, "%99[^;];%d;%49[^;];%d", nome, &idade, email, &id_turma) != 4) {
        sprintf(resposta, "ERRO;Formato de argumentos invalido.");
        return resposta;
    }

#ifdef _WIN32
    EnterCriticalSection(&g_file_mutex);
#else
    pthread_mutex_lock(&g_file_mutex);
#endif

    if (!id_existe(ARQUIVO_TURMAS, id_turma)) {
        sprintf(resposta, "ERRO;A turma com ID %d nao existe.", id_turma);
    } else {
        FILE *arquivo = fopen(ARQUIVO_ALUNOS, "a");
        if (arquivo == NULL) {
            sprintf(resposta, "ERRO;Nao foi possivel abrir o arquivo de alunos.");
        } else {
            int id_aluno = gerar_id_unico(ARQUIVO_ALUNOS);
            char matricula[20];
            sprintf(matricula, "RA%d", (rand() % 90000000) + 10000000);

            fprintf(arquivo, "%d;%s;%d;%s;%s;%d\n", id_aluno, nome, idade, matricula, email, id_turma);
            fclose(arquivo);
            
            sprintf(resposta, "SUCESSO;Aluno '%s' cadastrado com ID: %d.", nome, id_aluno);
        }
    }
    
#ifdef _WIN32
    LeaveCriticalSection(&g_file_mutex);
#else
    pthread_mutex_unlock(&g_file_mutex);
#endif
    return resposta;
}

char* listar_alunos_handler() {
#ifdef _WIN32
    EnterCriticalSection(&g_file_mutex);
#else
    pthread_mutex_lock(&g_file_mutex);
#endif
    FILE *arquivo = fopen(ARQUIVO_ALUNOS, "r");
    if (arquivo == NULL) {
#ifdef _WIN32
        LeaveCriticalSection(&g_file_mutex);
#else
        pthread_mutex_unlock(&g_file_mutex);
#endif
        char* resp = malloc(50);
        strcpy(resp, "VAZIO;Nenhum aluno cadastrado.");
        return resp;
    }
    
    char* resposta = malloc(TAMANHO_BUFFER * 5);
    strcpy(resposta, "DADOS;");
    char linha[MAX_LINHA];

    while (fgets(linha, sizeof(linha), arquivo)) {
        linha[strcspn(linha, "\n")] = 0;
        strcat(resposta, linha);
        strcat(resposta, "|");
    }
    fclose(arquivo);

#ifdef _WIN32
    LeaveCriticalSection(&g_file_mutex);
#else
    pthread_mutex_unlock(&g_file_mutex);
#endif

    if (strlen(resposta) > 6) {
        resposta[strlen(resposta) - 1] = '\0';
    }
    
    return resposta;
}

char* excluir_aluno_handler(char* args) {
    int id_excluir;
    char* resposta = malloc(100);

    if (sscanf(args, "%d", &id_excluir) != 1) {
        sprintf(resposta, "ERRO;ID do aluno invalido.");
        return resposta;
    }
    
#ifdef _WIN32
    EnterCriticalSection(&g_file_mutex);
#else
    pthread_mutex_lock(&g_file_mutex);
#endif
    
    if (!id_existe(ARQUIVO_ALUNOS, id_excluir)) {
        sprintf(resposta, "ERRO;Aluno com ID %d nao encontrado.", id_excluir);
    } else {
        FILE* original = fopen(ARQUIVO_ALUNOS, "r");
        FILE* temp = fopen("temp_alunos.csv", "w");
        if (!original || !temp) {
            sprintf(resposta, "ERRO;Falha ao abrir arquivos temporarios.");
        } else {
            char linha[MAX_LINHA];
            while (fgets(linha, sizeof(linha), original)) {
                int id_atual;
                sscanf(linha, "%d", &id_atual);
                if (id_atual != id_excluir) {
                    fputs(linha, temp);
                }
            }
            fclose(original);
            fclose(temp);
            
            remove(ARQUIVO_ALUNOS);
            rename("temp_alunos.csv", ARQUIVO_ALUNOS);
            
            sprintf(resposta, "SUCESSO;Aluno com ID %d excluido.", id_excluir);
        }
    }
#ifdef _WIN32
    LeaveCriticalSection(&g_file_mutex);
#else
    pthread_mutex_unlock(&g_file_mutex);
#endif
    return resposta;
}


// --- GESTÃO DE ATIVIDADES ---
char* cadastrar_atividade_handler(char* args) {
    int id_turma;
    char titulo[100], data_entrega[20];
    char* resposta = malloc(256);

    if (sscanf(args, "%d;%99[^;];%19[^\n]", &id_turma, titulo, data_entrega) != 3) {
        sprintf(resposta, "ERRO;Formato de argumentos invalido para CADASTRAR_ATIVIDADE.");
        return resposta;
    }

#ifdef _WIN32
    EnterCriticalSection(&g_file_mutex);
#else
    pthread_mutex_lock(&g_file_mutex);
#endif

    if (!id_existe(ARQUIVO_TURMAS, id_turma)) {
        sprintf(resposta, "ERRO;A turma com ID %d nao existe.", id_turma);
    } else {
        FILE *arquivo = fopen(ARQUIVO_ATIVIDADES, "a");
        if (arquivo == NULL) {
            sprintf(resposta, "ERRO;Nao foi possivel abrir o arquivo de atividades.");
        } else {
            int id_ativ = gerar_id_unico(ARQUIVO_ATIVIDADES);
            fprintf(arquivo, "%d;%d;%s;%s\n", id_ativ, id_turma, titulo, data_entrega);
            fclose(arquivo);
            sprintf(resposta, "SUCESSO;Atividade '%s' cadastrada com ID %d.", titulo, id_ativ);
        }
    }

#ifdef _WIN32
    LeaveCriticalSection(&g_file_mutex);
#else
    pthread_mutex_unlock(&g_file_mutex);
#endif
    return resposta;
}

char* listar_atividades_handler() {
#ifdef _WIN32
    EnterCriticalSection(&g_file_mutex);
#else
    pthread_mutex_lock(&g_file_mutex);
#endif

    FILE *arquivo = fopen(ARQUIVO_ATIVIDADES, "r");
    if (arquivo == NULL) {
#ifdef _WIN32
        LeaveCriticalSection(&g_file_mutex);
#else
        pthread_mutex_unlock(&g_file_mutex);
#endif
        char* resp = malloc(50);
        strcpy(resp, "VAZIO;Nenhuma atividade cadastrada.");
        return resp;
    }
    
    char* resposta = malloc(TAMANHO_BUFFER * 3);
    strcpy(resposta, "DADOS;");
    char linha[MAX_LINHA];
    while (fgets(linha, sizeof(linha), arquivo)) {
        linha[strcspn(linha, "\n")] = 0;
        strcat(resposta, linha);
        strcat(resposta, "|");
    }
    fclose(arquivo);

#ifdef _WIN32
    LeaveCriticalSection(&g_file_mutex);
#else
    pthread_mutex_unlock(&g_file_mutex);
#endif

    if(strlen(resposta) > 6) {
        resposta[strlen(resposta) - 1] = '\0';
    }
    
    return resposta;
}


// --- GESTÃO DE NOTAS ---
char* cadastrar_nota_handler(char* args) {
    int id_aluno, id_materia;
    char tipo_nota[10];
    float valor_nota;
    char* resposta = malloc(256);

    if (sscanf(args, "%d;%d;%9[^;];%f", &id_aluno, &id_materia, tipo_nota, &valor_nota) != 4) {
        sprintf(resposta, "ERRO;Formato de argumentos invalido para CADASTRAR_NOTA.");
        return resposta;
    }

#ifdef _WIN32
    EnterCriticalSection(&g_file_mutex);
#else
    pthread_mutex_lock(&g_file_mutex);
#endif

    if (!id_existe(ARQUIVO_ALUNOS, id_aluno)) {
        sprintf(resposta, "ERRO;O aluno com ID %d nao existe.", id_aluno);
    } else if (!id_existe(ARQUIVO_MATERIAS, id_materia)) {
        sprintf(resposta, "ERRO;A materia com ID %d nao existe.", id_materia);
    } else {
        FILE *arquivo = fopen(ARQUIVO_NOTAS, "a");
        if (arquivo == NULL) {
            sprintf(resposta, "ERRO;Nao foi possivel abrir o arquivo de notas.");
        } else {
            fprintf(arquivo, "%d;%d;%s;%.2f\n", id_aluno, id_materia, tipo_nota, valor_nota);
            fclose(arquivo);
            sprintf(resposta, "SUCESSO;Nota %s (%.2f) registrada para o aluno ID %d.", tipo_nota, valor_nota, id_aluno);
        }
    }
#ifdef _WIN32
    LeaveCriticalSection(&g_file_mutex);
#else
    pthread_mutex_unlock(&g_file_mutex);
#endif
    return resposta;
}

char* listar_notas_handler(){
#ifdef _WIN32
    EnterCriticalSection(&g_file_mutex);
#else
    pthread_mutex_lock(&g_file_mutex);
#endif
    FILE *arquivo = fopen(ARQUIVO_NOTAS, "r");
    if (arquivo == NULL) {
#ifdef _WIN32
        LeaveCriticalSection(&g_file_mutex);
#else
        pthread_mutex_unlock(&g_file_mutex);
#endif
        char* resp = malloc(50);
        strcpy(resp, "VAZIO;Nenhuma nota cadastrada.");
        return resp;
    }
    
    char* resposta = malloc(TAMANHO_BUFFER * 5);
    strcpy(resposta, "DADOS;");
    char linha[MAX_LINHA];

    while (fgets(linha, sizeof(linha), arquivo)) {
        linha[strcspn(linha, "\n")] = 0;
        strcat(resposta, linha);
        strcat(resposta, "|");
    }
    fclose(arquivo);

#ifdef _WIN32
    LeaveCriticalSection(&g_file_mutex);
#else
    pthread_mutex_unlock(&g_file_mutex);
#endif

    if (strlen(resposta) > 6) {
        resposta[strlen(resposta) - 1] = '\0';
    }
    
    return resposta;
}


// --- GESTÃO DE DIÁRIO E MENSAGENS ---
char* registrar_aula_handler(char* args) {
    int id_turma;
    char data[20], conteudo[200], presentes[512];
    char* resposta = malloc(256);

    if (sscanf(args, "%d;%19[^;];%199[^;];%511[^\n]", &id_turma, data, conteudo, presentes) != 4) {
        sprintf(resposta, "ERRO;Formato de argumentos invalido para REGISTRAR_AULA.");
        return resposta;
    }

#ifdef _WIN32
    EnterCriticalSection(&g_file_mutex);
#else
    pthread_mutex_lock(&g_file_mutex);
#endif

    char nome_arquivo_diario[50];
    sprintf(nome_arquivo_diario, "diario_turma_%d.csv", id_turma);

    FILE *arquivo = fopen(nome_arquivo_diario, "a");
    if (arquivo == NULL) {
        sprintf(resposta, "ERRO;Nao foi possivel abrir o arquivo de diario para a turma %d.", id_turma);
    } else {
        fprintf(arquivo, "%s;%s;%s\n", data, conteudo, presentes);
        fclose(arquivo);
        sprintf(resposta, "SUCESSO;Aula registrada no diario da turma %d.", id_turma);
    }

#ifdef _WIN32
    LeaveCriticalSection(&g_file_mutex);
#else
    pthread_mutex_unlock(&g_file_mutex);
#endif
    return resposta;
}

char* listar_diario_handler(char* args) {
    int id_turma;
    if (sscanf(args, "%d", &id_turma) != 1) {
        char* resp = malloc(50);
        strcpy(resp, "ERRO;ID de turma invalido.");
        return resp;
    }
    
#ifdef _WIN32
    EnterCriticalSection(&g_file_mutex);
#else
    pthread_mutex_lock(&g_file_mutex);
#endif

    char nome_arquivo[50];
    sprintf(nome_arquivo, "diario_turma_%d.csv", id_turma);
    
    FILE *arquivo = fopen(nome_arquivo, "r");
    if (arquivo == NULL) {
#ifdef _WIN32
        LeaveCriticalSection(&g_file_mutex);
#else
        pthread_mutex_unlock(&g_file_mutex);
#endif
        char* resp = malloc(100);
        sprintf(resp, "VAZIO;Nenhum diario encontrado para a turma %d.", id_turma);
        return resp;
    }
    
    char* resposta = malloc(TAMANHO_BUFFER * 5);
    strcpy(resposta, "DADOS;");
    char linha[MAX_LINHA];
    while (fgets(linha, sizeof(linha), arquivo)) {
        linha[strcspn(linha, "\n")] = 0;
        strcat(resposta, linha);
        strcat(resposta, "|");
    }
    fclose(arquivo);

#ifdef _WIN32
    LeaveCriticalSection(&g_file_mutex);
#else
    pthread_mutex_unlock(&g_file_mutex);
#endif

    if(strlen(resposta) > 6) {
        resposta[strlen(resposta) - 1] = '\0';
    }
    
    return resposta;
}

char* postar_mensagem_handler(char* args) {
    int id_turma;
    char data[20], mensagem[512];
    char* resposta = malloc(256);

    if (sscanf(args, "%d;%19[^;];%511[^\n]", &id_turma, data, mensagem) != 3) {
        sprintf(resposta, "ERRO;Formato de argumentos invalido para POSTAR_MENSAGEM.");
        return resposta;
    }

#ifdef _WIN32
    EnterCriticalSection(&g_file_mutex);
#else
    pthread_mutex_lock(&g_file_mutex);
#endif

    FILE *arquivo = fopen(ARQUIVO_MENSAGENS, "a");
    if (arquivo == NULL) {
        sprintf(resposta, "ERRO;Nao foi possivel abrir o mural de avisos.");
    } else {
        fprintf(arquivo, "%d;%s;%s\n", id_turma, data, mensagem);
        fclose(arquivo);
        sprintf(resposta, "SUCESSO;Mensagem postada para a turma %d.", id_turma);
    }
#ifdef _WIN32
    LeaveCriticalSection(&g_file_mutex);
#else
    pthread_mutex_unlock(&g_file_mutex);
#endif
    return resposta;
}

char* listar_mensagens_handler() {
#ifdef _WIN32
    EnterCriticalSection(&g_file_mutex);
#else
    pthread_mutex_lock(&g_file_mutex);
#endif
    FILE *arquivo = fopen(ARQUIVO_MENSAGENS, "r");
    if (arquivo == NULL) {
#ifdef _WIN32
        LeaveCriticalSection(&g_file_mutex);
#else
        pthread_mutex_unlock(&g_file_mutex);
#endif
        char* resp = malloc(50);
        strcpy(resp, "VAZIO;Nenhuma mensagem no mural.");
        return resp;
    }
    
    char* resposta = malloc(TAMANHO_BUFFER * 5);
    strcpy(resposta, "DADOS;");
    char linha[MAX_LINHA];

    while (fgets(linha, sizeof(linha), arquivo)) {
        linha[strcspn(linha, "\n")] = 0;
        strcat(resposta, linha);
        strcat(resposta, "|");
    }
    fclose(arquivo);

#ifdef _WIN32
    LeaveCriticalSection(&g_file_mutex);
#else
    pthread_mutex_unlock(&g_file_mutex);
#endif

    if (strlen(resposta) > 6) {
        resposta[strlen(resposta) - 1] = '\0';
    }
    
    return resposta;
}


// --- GESTÃO DE SISTEMA (LOG, BACKUP, IA) ---
char* log_handler(char* args) {
#ifdef _WIN32
    EnterCriticalSection(&g_file_mutex);
#else
    pthread_mutex_lock(&g_file_mutex);
#endif
    FILE* arquivo = fopen(ARQUIVO_LOG, "a");
    if (arquivo == NULL) {
#ifdef _WIN32
        LeaveCriticalSection(&g_file_mutex);
#else
        pthread_mutex_unlock(&g_file_mutex);
#endif
        char* resp = malloc(50);
        strcpy(resp, "ERRO;Nao foi possivel abrir o arquivo de log.");
        return resp;
    }

    time_t t = time(NULL);
    struct tm *tm_info = localtime(&t);
    char timestamp[26];
    strftime(timestamp, 26, "%Y-%m-%d %H:%M:%S", tm_info);

    fprintf(arquivo, "%s;%s\n", timestamp, args);
    fclose(arquivo);

#ifdef _WIN32
    LeaveCriticalSection(&g_file_mutex);
#else
    pthread_mutex_unlock(&g_file_mutex);
#endif

    char* resp = malloc(50);
    strcpy(resp, "SUCESSO;Log registrado.");
    return resp;
}

char* listar_logs_handler() {
#ifdef _WIN32
    EnterCriticalSection(&g_file_mutex);
#else
    pthread_mutex_lock(&g_file_mutex);
#endif
    FILE* arquivo = fopen(ARQUIVO_LOG, "r");
    if (arquivo == NULL) {
#ifdef _WIN32
        LeaveCriticalSection(&g_file_mutex);
#else
        pthread_mutex_unlock(&g_file_mutex);
#endif
        char* resp = malloc(50);
        strcpy(resp, "VAZIO;Nenhum log encontrado.");
        return resp;
    }

    char* resposta = malloc(TAMANHO_BUFFER * 10);
    strcpy(resposta, "DADOS;");
    char linha[MAX_LINHA];
    while(fgets(linha, sizeof(linha), arquivo)) {
        linha[strcspn(linha, "\n")] = 0;
        strcat(resposta, linha);
        strcat(resposta, "|");
    }
    fclose(arquivo);

#ifdef _WIN32
    LeaveCriticalSection(&g_file_mutex);
#else
    pthread_mutex_unlock(&g_file_mutex);
#endif
    
    if (strlen(resposta) > 6) {
        resposta[strlen(resposta)-1] = '\0';
    }
    return resposta;
}

char* backup_handler() {
#ifdef _WIN32
    EnterCriticalSection(&g_file_mutex);
#else
    pthread_mutex_lock(&g_file_mutex);
#endif
    printf("\nIniciando backup...\n");
#ifdef _WIN32
    _mkdir("backup");
#else
    mkdir("backup", 0777);
#endif

    time_t t = time(NULL);
    struct tm tm = *localtime(&t);
    char timestamp[40];
    sprintf(timestamp, "%d%02d%02d_%02d%02d%02d", tm.tm_year + 1900, tm.tm_mon + 1, tm.tm_mday, tm.tm_hour, tm.tm_min, tm.tm_sec);

    const char* arquivos[] = {ARQUIVO_CURSOS, ARQUIVO_MATERIAS, ARQUIVO_TURMAS, ARQUIVO_ALUNOS, ARQUIVO_ATIVIDADES, ARQUIVO_NOTAS, ARQUIVO_MENSAGENS, ARQUIVO_LOG};
    int num_arquivos = sizeof(arquivos) / sizeof(arquivos[0]);

    for (int i = 0; i < num_arquivos; i++) {
        FILE* original = fopen(arquivos[i], "rb");
        if (original) {
            char nome_backup[100];
            sprintf(nome_backup, "backup/%s_%s.bak", arquivos[i], timestamp);
            FILE* backup = fopen(nome_backup, "wb");
            if (backup) {
                char buffer[1024];
                size_t bytes;
                while ((bytes = fread(buffer, 1, sizeof(buffer), original)) > 0) {
                    fwrite(buffer, 1, bytes, backup);
                }
                fclose(backup);
                printf("Backup de '%s' criado em '%s'\n", arquivos[i], nome_backup);
            }
            fclose(original);
        }
    }
    printf("\nBackup concluido!\n");
#ifdef _WIN32
    LeaveCriticalSection(&g_file_mutex);
#else
    pthread_mutex_unlock(&g_file_mutex);
#endif
    char* resposta = malloc(50);
    strcpy(resposta, "SUCESSO;Backup realizado no servidor.");
    return resposta;
}

char* limpar_arquivo_handler(const char* nome_arquivo) {
#ifdef _WIN32
    EnterCriticalSection(&g_file_mutex);
#else
    pthread_mutex_lock(&g_file_mutex);
#endif
    FILE* arquivo = fopen(nome_arquivo, "w");
    if (arquivo == NULL) {
#ifdef _WIN32
        LeaveCriticalSection(&g_file_mutex);
#else
        pthread_mutex_unlock(&g_file_mutex);
#endif
        char* resp = malloc(100);
        sprintf(resp, "ERRO;Nao foi possivel limpar o arquivo %s.", nome_arquivo);
        return resp;
    }
    fclose(arquivo);
#ifdef _WIN32
    LeaveCriticalSection(&g_file_mutex);
#else
    pthread_mutex_unlock(&g_file_mutex);
#endif
    char* resp = malloc(100);
    sprintf(resp, "SUCESSO;Arquivo %s foi limpo.", nome_arquivo);
    return resp;
}

char* analisar_desempenho_ia_handler() {
#ifdef _WIN32
    EnterCriticalSection(&g_file_mutex);
#else
    pthread_mutex_lock(&g_file_mutex);
#endif
    FILE* arq_notas = fopen(ARQUIVO_NOTAS, "r");
    if (arq_notas == NULL) {
#ifdef _WIN32
        LeaveCriticalSection(&g_file_mutex);
#else
        pthread_mutex_unlock(&g_file_mutex);
#endif
        char* resp = malloc(100);
        strcpy(resp, "ERRO;Arquivo de notas nao encontrado para analise.");
        return resp;
    }

    char* resposta = malloc(TAMANHO_BUFFER);
    strcpy(resposta, "IA_RESULTADO;");
    char linha[MAX_LINHA];
    int encontrou_risco = 0;

    while(fgets(linha, sizeof(linha), arq_notas)) {
        int id_aluno;
        float nota;
        if(sscanf(linha, "%d;%*d;%*[^;];%f", &id_aluno, &nota) == 2) {
            if (nota < 5.0) {
                char aluno_em_risco[20];
                sprintf(aluno_em_risco, "%d,", id_aluno);
                strcat(resposta, aluno_em_risco);
                encontrou_risco = 1;
            }
        }
    }
    fclose(arq_notas);
    
#ifdef _WIN32
    LeaveCriticalSection(&g_file_mutex);
#else
    pthread_mutex_unlock(&g_file_mutex);
#endif

    if (encontrou_risco) {
        resposta[strlen(resposta) - 1] = '\0';
    } else {
        strcat(resposta, "NENHUM");
    }

    return resposta;
}


// --- Funções Utilitárias ---
int id_existe(const char* nome_arquivo, int id_para_verificar) {
    FILE* arquivo = fopen(nome_arquivo, "r");
    if (arquivo == NULL) return 0;
    char linha[MAX_LINHA];
    while (fgets(linha, sizeof(linha), arquivo)) {
        int id_atual;
        if (sscanf(linha, "%d", &id_atual) == 1 && id_atual == id_para_verificar) {
            fclose(arquivo);
            return 1;
        }
    }
    fclose(arquivo);
    return 0;
}

int gerar_id_unico(const char* nome_arquivo) {
    int novo_id;
    do {
        novo_id = (rand() % 9000) + 1000;
    } while (id_existe(nome_arquivo, novo_id));
    return novo_id;
}

int verificar_alunos_na_turma(int id_turma_busca) {
    FILE* arquivo = fopen(ARQUIVO_ALUNOS, "r");
    if (arquivo == NULL) return 0;
    char linha[MAX_LINHA];
    while (fgets(linha, sizeof(linha), arquivo)) {
        int id_turma;
        if (sscanf(linha, "%*d;%*[^;];%*d;%*[^;];%*[^;];%d", &id_turma) == 1) {
            if (id_turma == id_turma_busca) {
                fclose(arquivo);
                return 1;
            }
        }
    }
    fclose(arquivo);
    return 0;
}

int verificar_materias_no_curso(int id_curso_busca) {
    FILE* arquivo = fopen(ARQUIVO_MATERIAS, "r");
    if (arquivo == NULL) return 0;
    char linha[MAX_LINHA];
    while (fgets(linha, sizeof(linha), arquivo)) {
        int id_curso;
        if (sscanf(linha, "%*d;%*[^;];%d;%*[^;];%*s", &id_curso) == 2) { 
            if (id_curso == id_curso_busca) {
                fclose(arquivo);
                return 1;
            }
        }
    }
    fclose(arquivo);
    return 0;
}

